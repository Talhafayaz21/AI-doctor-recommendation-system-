import faiss
import numpy as np
import os
import pickle
import logging
from typing import List, Tuple, Optional

from .embeddings import EMBEDDING_DIM, is_available

logger = logging.getLogger(__name__)

INDEX_PATH = os.path.join(os.path.dirname(__file__), "../../data/rag_index")

class VectorStore:
    def __init__(self):
        self.index = faiss.IndexFlatL2(EMBEDDING_DIM)
        self.documents: List[str] = []
        self.is_loaded = False
        self._embeddings_available = is_available()

    def add_documents(self, docs: List[str], embeddings: Optional[List[Optional[List[float]]]]) -> bool:
        """
        Add documents + embeddings with improved error handling.

        Args:
            docs: List of document texts
            embeddings: List of embedding vectors (can contain None for failed embeddings)

        Returns:
            True if any documents were successfully added
        """
        if not docs:
            logger.warning("No documents provided to add")
            return False

        if not embeddings:
            logger.error("No embeddings provided")
            return False

        if not self._embeddings_available:
            logger.warning("Embeddings system not available - vector store operations limited")
            return False

        # Filter out documents with failed embeddings
        valid_pairs = [
            (doc, emb) for doc, emb in zip(docs, embeddings)
            if emb is not None and len(emb) == EMBEDDING_DIM
        ]

        if not valid_pairs:
            logger.error("No valid embeddings found - all embeddings failed")
            return False

        try:
            filtered_docs, filtered_embeddings = zip(*valid_pairs)
            vectors = np.array(filtered_embeddings).astype("float32")

            self.index.add(vectors)
            self.documents.extend(filtered_docs)

            logger.info(f"Added {len(filtered_docs)}/{len(docs)} documents to vector store")
            return True

        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return False

    def search(self, query_embedding: Optional[List[float]], k: int = 3) -> List[str]:
        """
        Search for top-k most similar documents.

        Args:
            query_embedding: Query vector (must be same dimension as index)
            k: Number of results to return

        Returns:
            List of document texts (empty if no results or errors)
        """
        if not query_embedding:
            logger.warning("No query embedding provided")
            return []

        if len(query_embedding) != EMBEDDING_DIM:
            logger.error(f"Query embedding dimension {len(query_embedding)} != expected {EMBEDDING_DIM}")
            return []

        if not self.is_loaded:
            logger.warning("Vector store not loaded - cannot perform search")
            return []

        if self.index.ntotal == 0:
            logger.warning("Vector store is empty - no documents to search")
            return []

        try:
            query = np.array([query_embedding]).astype("float32")
            k = min(k, self.index.ntotal)  # Don't ask for more than we have

            distances, indices = self.index.search(query, k)

            results = []
            for idx in indices[0]:
                if idx < len(self.documents) and idx >= 0:
                    results.append(self.documents[idx])

            logger.debug(f"Search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def save(self, path: str = INDEX_PATH):
        """
        Save the vector store to disk.

        Args:
            path: Directory path to save to

        Returns:
            True if save was successful
        """
        try:
            os.makedirs(path, exist_ok=True)

            # Save FAISS index
            index_path = os.path.join(path, "index.faiss")
            faiss.write_index(self.index, index_path)

            # Save documents list
            docs_path = os.path.join(path, "docs.pkl")
            with open(docs_path, "wb") as f:
                pickle.dump(self.documents, f)

            # Save metadata
            metadata = {
                "embedding_dim": EMBEDDING_DIM,
                "total_documents": len(self.documents),
                "index_vectors": self.index.ntotal if hasattr(self.index, 'ntotal') else 0
            }
            metadata_path = os.path.join(path, "metadata.pkl")
            with open(metadata_path, "wb") as f:
                pickle.dump(metadata, f)

            logger.info(f"Vector store saved to {path} ({len(self.documents)} documents)")
            return True

        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")
            return False

    def load(self, path: str = INDEX_PATH):
        """
        Load the vector store from disk.

        Args:
            path: Directory path to load from

        Returns:
            True if load was successful
        """
        try:
            index_path = os.path.join(path, "index.faiss")
            docs_path = os.path.join(path, "docs.pkl")
            metadata_path = os.path.join(path, "metadata.pkl")

            # Check if required files exist
            if not os.path.exists(index_path) or not os.path.exists(docs_path):
                logger.warning(f"Required index files not found at {path}")
                return False

            # Load FAISS index
            self.index = faiss.read_index(index_path)

            # Load documents
            with open(docs_path, "rb") as f:
                self.documents = pickle.load(f)

            # Load and validate metadata if available
            if os.path.exists(metadata_path):
                with open(metadata_path, "rb") as f:
                    metadata = pickle.load(f)

                stored_dim = metadata.get("embedding_dim", EMBEDDING_DIM)
                if stored_dim != EMBEDDING_DIM:
                    logger.warning(f"Embedding dimension mismatch: stored={stored_dim}, current={EMBEDDING_DIM}")

            # Validate loaded data
            index_vectors = self.index.ntotal if hasattr(self.index, 'ntotal') else 0
            if index_vectors != len(self.documents):
                logger.warning(f"Index/documents mismatch: {index_vectors} vectors, {len(self.documents)} documents")

            self.is_loaded = True
            logger.info(f"Vector store loaded from {path} ({len(self.documents)} documents)")
            return True

        except Exception as e:
            logger.error(f"Failed to load vector store: {e}")
            return False

    def get_stats(self) -> dict:
        """Get vector store statistics"""
        return {
            "total_documents": len(self.documents),
            "vector_dimension": EMBEDDING_DIM,
            "is_loaded": self.is_loaded
        }


# Global instance
vector_store = VectorStore()