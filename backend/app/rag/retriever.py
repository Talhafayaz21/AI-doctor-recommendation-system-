from typing import List, Optional
import logging
from .embeddings import get_embedding, is_available
from .vector_store import vector_store

logger = logging.getLogger(__name__)


def retrieve_context(query: str, k: int = 3) -> List[str]:
    """
    Retrieve relevant documents for a query using vector search or fallback methods.

    Args:
        query: Search query string
        k: Number of results to return

    Returns:
        List of relevant document texts
    """
    try:
        # Validate input
        if not query or not query.strip():
            logger.warning("Empty query provided to retrieve_context")
            return []

        query = query.strip()

        # Check if embeddings system is available
        if not is_available():
            logger.info("Embeddings system not available, using keyword fallback")
            return _fallback_search(query, k)

        # Check if vector store is loaded
        if not vector_store.is_loaded:
            logger.info("Vector store not loaded, attempting to load...")
            if not vector_store.load():
                logger.warning("Failed to load vector store, using keyword fallback")
                return _fallback_search(query, k)

        # Try to get embedding for the query
        query_embedding = get_embedding(query)
        if query_embedding:
            # Use vector search
            results = vector_store.search(query_embedding, k)
            if results:
                logger.info(f"Vector search: Retrieved {len(results)} documents for query: {query[:50]}...")
                return results
            else:
                logger.info("Vector search returned no results, trying keyword fallback")
                return _fallback_search(query, k)
        else:
            # Fallback to keyword search
            logger.warning("Failed to generate query embedding, using keyword fallback")
            return _fallback_search(query, k)

    except Exception as e:
        logger.error(f"Error in retrieve_context: {e}")
        return _fallback_search(query, k)


def _fallback_search(query: str, k: int = 3) -> List[str]:
    """
    Fallback keyword-based search when embeddings are unavailable.

    Args:
        query: Search query string
        k: Number of results to return

    Returns:
        List of relevant document contents
    """
    try:
        from .medical_kb import search_documents_by_keyword, MEDICAL_DOCUMENTS

        # Extract key medical terms from query (remove common words and punctuation)
        import re
        query_lower = query.lower()
        # Remove punctuation and normalize
        query_clean = re.sub(r'[^\w\s]', ' ', query_lower)

        # Common stop words to filter out
        stop_words = {
            'what', 'causes', 'symptoms', 'of', 'the', 'is', 'are', 'how', 'when', 'why',
            'where', 'who', 'which', 'that', 'this', 'these', 'those', 'a', 'an', 'and',
            'or', 'but', 'if', 'then', 'else', 'for', 'with', 'about', 'into', 'through',
            'during', 'before', 'after', 'above', 'below', 'between', 'among', 'can',
            'could', 'should', 'would', 'does', 'do', 'did', 'has', 'have', 'had',
            'will', 'may', 'might', 'must', 'i', 'me', 'my', 'you', 'your', 'it', 'its'
        }

        # Extract meaningful terms
        words = query_clean.split()
        key_terms = [word for word in words if word not in stop_words and len(word) > 2]

        # If no key terms found, use original query
        search_query = ' '.join(key_terms) if key_terms else query_lower.strip()

        if not search_query:
            logger.warning("No searchable terms found in query")
            return _get_default_medical_info(k)

        # Primary search
        keyword_results = search_documents_by_keyword(search_query)

        if keyword_results:
            # Prioritize by relevance: exact title matches first, then content matches
            exact_title_matches = []
            content_matches = []

            for doc in keyword_results:
                title_lower = doc["title"].lower()
                content_lower = doc["content"].lower()

                # Check for exact term matches in title
                if any(term in title_lower for term in key_terms):
                    exact_title_matches.append(doc)
                else:
                    content_matches.append(doc)

            # Combine results with title matches prioritized
            prioritized_results = exact_title_matches + content_matches

            # Return content of top matches
            results = [doc["content"] for doc in prioritized_results[:k]]
            logger.info(f"Keyword search: Found {len(results)} documents for '{query}' (terms: {key_terms})")
            return results

        # If no direct matches, try individual key terms
        logger.info(f"No direct matches for '{search_query}', trying individual terms")
        for term in key_terms[:3]:  # Limit to first 3 terms to avoid too many searches
            term_results = search_documents_by_keyword(term)
            if term_results:
                results = [doc["content"] for doc in term_results[:k]]
                logger.info(f"Individual term search: Found {len(results)} documents for '{term}'")
                return results

        # If still no matches, return general medical information
        logger.info("No keyword matches found, returning general medical information")
        return _get_default_medical_info(k)

    except Exception as e:
        logger.error(f"Fallback search error: {e}")
        return ["Medical information is currently unavailable. Please consult a healthcare professional for advice."]


def _get_default_medical_info(k: int = 3) -> List[str]:
    """Return general medical information when no specific matches found"""
    try:
        from .medical_kb import MEDICAL_DOCUMENTS

        # Prioritize general wellness and emergency information
        priority_categories = ["general", "wellness", "emergency"]
        default_docs = []

        # First, get docs from priority categories
        for category in priority_categories:
            category_docs = [doc for doc in MEDICAL_DOCUMENTS if doc["category"] == category]
            default_docs.extend(category_docs)

        # Fill remaining slots with other categories if needed
        if len(default_docs) < k:
            remaining_docs = [doc for doc in MEDICAL_DOCUMENTS if doc["category"] not in priority_categories]
            default_docs.extend(remaining_docs[:k - len(default_docs)])

        return [doc["content"] for doc in default_docs[:k]]

    except Exception as e:
        logger.error(f"Error getting default medical info: {e}")
        return ["Please consult a healthcare professional for medical advice."]


def get_retrieval_stats() -> dict:
    """Get retrieval statistics"""
    return {
        "vector_store_stats": vector_store.get_stats(),
        "retriever_status": "active" if vector_store.is_loaded else "inactive"
    }