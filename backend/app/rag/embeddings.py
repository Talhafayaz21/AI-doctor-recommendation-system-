import os
import logging
import time
import hashlib
from functools import lru_cache
from typing import List, Optional, Dict, Any

from openai import OpenAI, RateLimitError, APIConnectionError, APIStatusError
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
EMBEDDING_MODEL   = "text-embedding-3-small"
EMBEDDING_DIM     = 1536          # dimensions for text-embedding-3-small
MAX_BATCH_SIZE    = 100           # OpenAI hard limit per request
MAX_RETRIES       = 3             # retry attempts on transient errors
RETRY_DELAY_SEC   = 1.5          # base delay; doubles each retry (exponential backoff)
MAX_INPUT_TOKENS  = 8191          # model's token limit — text is truncated if exceeded

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  VALIDATION HELPERS
# ─────────────────────────────────────────────
def _is_placeholder_key(key: str) -> bool:
    """Detect common placeholder strings people copy from docs/tutorials."""
    PLACEHOLDER_SIGNALS = ("your-", "here", "xxx", "placeholder", "sk-...")
    lowered = key.lower()
    return any(signal in lowered for signal in PLACEHOLDER_SIGNALS)


def _validate_api_key(key: Optional[str]) -> Optional[str]:
    """
    Return the key if it looks valid, otherwise return None with a clear log message.
    OpenAI keys start with 'sk-' and are at least 40 characters long.
    """
    if not key:
        logger.warning("OPENAI_API_KEY not found in environment — embeddings disabled.")
        return None

    if _is_placeholder_key(key):
        logger.warning(
            "OPENAI_API_KEY looks like a placeholder value. "
            "Replace it with a real key from https://platform.openai.com/api-keys"
        )
        return None

    if not key.startswith("sk-") or len(key) < 40:
        logger.warning(
            "OPENAI_API_KEY format looks incorrect "
            "(expected 'sk-...' with 40+ characters)."
        )
        return None

    return key


# ─────────────────────────────────────────────
#  CLIENT INITIALISATION
# ─────────────────────────────────────────────
def _build_client() -> Optional[OpenAI]:
    """
    Build and validate the OpenAI client once at module load.
    Returns None if the key is missing/invalid so callers can gracefully degrade.
    """
    raw_key = os.getenv("OPENAI_API_KEY")
    valid_key = _validate_api_key(raw_key)

    if not valid_key:
        return None

    try:
        client = OpenAI(api_key=valid_key)
        # Cheap smoke-test: listing models verifies auth without spending money
        client.models.list()
        logger.info("OpenAI client initialised and authenticated successfully.")
        return client

    except APIConnectionError:
        logger.error("Could not reach OpenAI API — check your internet connection.")
    except APIStatusError as e:
        logger.error(
            "OpenAI rejected the API key (status %s). "
            "Verify the key at https://platform.openai.com/api-keys. Error: %s",
            e.status_code, e.message,
        )
    except Exception as e:
        logger.error("Unexpected error initialising OpenAI client: %s", e)

    return None


# Module-level singleton — built once, shared by all functions below
_client: Optional[OpenAI] = _build_client()


# ─────────────────────────────────────────────
#  RETRY LOGIC
# ─────────────────────────────────────────────
def _with_retries(fn, *args, **kwargs) -> Any:
    """
    Call fn(*args, **kwargs) with exponential backoff on transient failures.

    Retries on:  RateLimitError, APIConnectionError (network blips)
    Raises on:   APIStatusError with non-retryable status codes (4xx except 429)
    """
    delay = RETRY_DELAY_SEC
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)

        except RateLimitError:
            if attempt == MAX_RETRIES:
                logger.error("Rate limit hit and all %d retries exhausted.", MAX_RETRIES)
                raise
            logger.warning(
                "Rate limit hit — waiting %.1fs before retry %d/%d …",
                delay, attempt, MAX_RETRIES,
            )
            time.sleep(delay)
            delay *= 2   # exponential backoff

        except APIConnectionError:
            if attempt == MAX_RETRIES:
                logger.error("Connection error and all %d retries exhausted.", MAX_RETRIES)
                raise
            logger.warning(
                "Connection error — waiting %.1fs before retry %d/%d …",
                delay, attempt, MAX_RETRIES,
            )
            time.sleep(delay)
            delay *= 2

        except APIStatusError as e:
            # 429 is rate-limit (already caught above); other 4xx are caller errors
            if e.status_code != 429:
                logger.error("Non-retryable API error %s: %s", e.status_code, e.message)
                raise
            time.sleep(delay)
            delay *= 2


# ─────────────────────────────────────────────
#  TEXT PREPROCESSING
# ─────────────────────────────────────────────
def _sanitise(text: str) -> str:
    """
    Light preprocessing before embedding:
    - Strip surrounding whitespace
    - Collapse internal newlines/tabs to single spaces (noisy for embeddings)
    - Truncate to MAX_INPUT_TOKENS characters as a rough guard
      (proper token counting would require tiktoken)
    """
    text = text.strip()
    text = " ".join(text.split())          # collapse all whitespace
    # Rough character-based guard (≈4 chars/token on average)
    char_limit = MAX_INPUT_TOKENS * 4
    if len(text) > char_limit:
        logger.warning(
            "Text truncated from %d to %d characters to stay within token limit.",
            len(text), char_limit,
        )
        text = text[:char_limit]
    return text


# ─────────────────────────────────────────────
#  IN-MEMORY CACHE  (optional, zero dependencies)
# ─────────────────────────────────────────────
_embedding_cache: Dict[str, List[float]] = {}

def _cache_key(text: str, model: str) -> str:
    """Stable hash so the same text+model always hits the same cache entry."""
    return hashlib.sha256(f"{model}::{text}".encode()).hexdigest()


# ─────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────
def get_embedding(
    text: str,
    *,
    model: str = EMBEDDING_MODEL,
    use_cache: bool = True,
) -> Optional[List[float]]:
    """
    Convert a single piece of text to a dense embedding vector.

    Args:
        text:       The input string to embed.
        model:      OpenAI embedding model name. Defaults to EMBEDDING_MODEL.
        use_cache:  Cache results in memory to avoid re-embedding identical text.

    Returns:
        A list of floats (length = EMBEDDING_DIM) or None on any failure.

    Example:
        >>> vec = get_embedding("semantic search is powerful")
        >>> len(vec)
        1536
    """
    if not _client:
        logger.warning("OpenAI client unavailable — returning None for single embedding.")
        return None

    if not text or not text.strip():
        logger.warning("Empty text passed to get_embedding — returning None.")
        return None

    clean = _sanitise(text)

    # ── Cache lookup ──────────────────────────
    key = _cache_key(clean, model)
    if use_cache and key in _embedding_cache:
        logger.debug("Embedding cache hit for text (%.40s…)", clean)
        return _embedding_cache[key]

    # ── API call with retries ─────────────────
    try:
        response = _with_retries(
            _client.embeddings.create,
            model=model,
            input=clean,
        )
        vector = response.data[0].embedding

        if use_cache:
            _embedding_cache[key] = vector

        logger.debug(
            "Embedding generated: model=%s, dims=%d, tokens_used=%d",
            model, len(vector), response.usage.total_tokens,
        )
        return vector

    except Exception as e:
        logger.error("get_embedding failed after retries: %s", e)
        return None


def get_embeddings(
    texts: List[str],
    *,
    model: str = EMBEDDING_MODEL,
    use_cache: bool = True,
    batch_size: int = MAX_BATCH_SIZE,
) -> Optional[List[Optional[List[float]]]]:
    """
    Embed a list of texts in optimised batches.

    Texts already in the cache are resolved without an API call.
    The remaining texts are sent in batches of `batch_size`.
    Results are returned in the original input order.

    Args:
        texts:      List of strings to embed.
        model:      OpenAI embedding model name.
        use_cache:  Serve cached embeddings where available.
        batch_size: Max texts per API request (hard cap = MAX_BATCH_SIZE).

    Returns:
        A list of vectors in input order. Individual entries are None if their
        embedding failed. Returns None if the client is unavailable.

    Example:
        >>> vecs = get_embeddings(["hello", "world"])
        >>> len(vecs)
        2
    """
    if not _client:
        logger.warning("OpenAI client unavailable — returning None for batch embeddings.")
        return None

    if not texts:
        logger.warning("Empty list passed to get_embeddings — returning [].")
        return []

    # Sanitise all inputs upfront and track original positions
    cleaned    = [_sanitise(t) for t in texts]
    results    = [None] * len(cleaned)          # pre-allocate output slots
    to_fetch   = []                             # (original_index, cleaned_text) pairs

    # ── Resolve from cache where possible ────
    for i, text in enumerate(cleaned):
        if not text:
            logger.warning("Empty text at index %d — will be None in output.", i)
            continue
        key = _cache_key(text, model)
        if use_cache and key in _embedding_cache:
            results[i] = _embedding_cache[key]
        else:
            to_fetch.append((i, text))

    cache_hits  = len(cleaned) - len(to_fetch)
    logger.info(
        "Batch embed: %d total, %d cache hits, %d to fetch via API.",
        len(cleaned), cache_hits, len(to_fetch),
    )

    if not to_fetch:
        return results   # everything was cached

    # ── Clamp batch size to allowed maximum ──
    effective_batch = min(batch_size, MAX_BATCH_SIZE)

    # ── Send in batches ───────────────────────
    total_tokens = 0
    for batch_start in range(0, len(to_fetch), effective_batch):
        batch = to_fetch[batch_start : batch_start + effective_batch]
        indices, batch_texts = zip(*batch)

        try:
            response = _with_retries(
                _client.embeddings.create,
                model=model,
                input=list(batch_texts),
            )
            total_tokens += response.usage.total_tokens

            for item in response.data:
                # response.data order matches input order
                orig_idx = indices[item.index]
                vector   = item.embedding
                results[orig_idx] = vector

                if use_cache:
                    key = _cache_key(batch_texts[item.index], model)
                    _embedding_cache[key] = vector

        except Exception as e:
            logger.error(
                "Batch embedding failed for items %d–%d: %s",
                batch_start, batch_start + len(batch) - 1, e,
            )
            # Slots remain None — caller can detect partial failures

    successful = sum(1 for r in results if r is not None)
    logger.info(
        "Batch embed complete: %d/%d successful, total_tokens=%d.",
        successful, len(texts), total_tokens,
    )
    return results


def is_available() -> bool:
    """Return True if the embedding client is ready to use."""
    return _client is not None


def clear_cache() -> None:
    """Evict all in-memory cached embeddings (useful between test runs)."""
    count = len(_embedding_cache)
    _embedding_cache.clear()
    logger.info("Embedding cache cleared (%d entries removed).", count)


def cache_stats() -> Dict[str, int]:
    """Inspect current cache state without modifying it."""
    return {
        "cached_entries": len(_embedding_cache),
        "estimated_memory_bytes": len(_embedding_cache) * EMBEDDING_DIM * 4,  # float32
    }