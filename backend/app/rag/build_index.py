#!/usr/bin/env python3
"""
RAG Index Builder
Creates and maintains the vector index for medical documents.
"""

import os
import sys
import logging
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.embeddings import get_embeddings
from rag.vector_store import vector_store
from rag.medical_kb import get_all_document_texts, get_document_titles, MEDICAL_DOCUMENTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_index():
    """
    Build the RAG index from medical knowledge base with improved error handling.

    Returns:
        True if index was built and saved successfully
    """
    logger.info("Starting RAG index build...")

    try:
        # Get documents and titles
        documents = get_all_document_texts()
        titles = get_document_titles()

        if not documents or not titles:
            logger.error("No documents found in medical knowledge base")
            return False

        if len(documents) != len(titles):
            logger.error(f"Document/title mismatch: {len(documents)} docs, {len(titles)} titles")
            return False

        # Combine titles and content for better context
        full_docs = []
        for i, (title, content) in enumerate(zip(titles, documents)):
            full_doc = f"Title: {title}\n\nContent: {content}"
            full_docs.append(full_doc)

        logger.info(f"Processing {len(full_docs)} medical documents...")

        # Get embeddings with proper error handling
        embeddings = get_embeddings(full_docs)

        if not embeddings:
            logger.error("Failed to generate embeddings - cannot build index")
            return False

        # Check for partial failures
        successful_embeddings = sum(1 for emb in embeddings if emb is not None)
        if successful_embeddings == 0:
            logger.error("All embeddings failed - cannot build index")
            return False

        if successful_embeddings < len(embeddings):
            logger.warning(f"Only {successful_embeddings}/{len(embeddings)} embeddings succeeded")

        logger.info(f"Generated {successful_embeddings} embeddings successfully")

        # Add to vector store (now handles None embeddings gracefully)
        success = vector_store.add_documents(full_docs, embeddings)

        if success:
            # Save the index
            save_success = vector_store.save()
            if save_success:
                logger.info("RAG index built and saved successfully!")
                stats = vector_store.get_stats()
                logger.info(f"Index stats: {stats}")
                return True
            else:
                logger.error("Failed to save index")
                return False
        else:
            logger.error("Failed to add documents to vector store")
            return False

    except Exception as e:
        logger.error(f"Unexpected error building index: {e}")
        return False


def load_index():
    """Load existing RAG index"""
    logger.info("Loading RAG index...")
    success = vector_store.load()
    if success:
        stats = vector_store.get_stats()
        logger.info(f"Index loaded successfully: {stats}")
        return True
    else:
        logger.warning("Failed to load index - will need to rebuild")
        return False


def test_index():
    """Test the index with sample queries"""
    logger.info("Testing RAG index...")

    test_queries = [
        "chest pain heart attack",
        "diabetes symptoms",
        "headache causes",
        "fever in children"
    ]

    try:
        from .retriever import retrieve_context, get_retrieval_stats

        # Show system stats
        stats = get_retrieval_stats()
        logger.info(f"System stats: {stats}")

        # Test each query
        for i, test_query in enumerate(test_queries, 1):
            logger.info(f"\n--- Test Query {i}: '{test_query}' ---")

            results = retrieve_context(test_query, k=2)

            if results:
                logger.info(f"Retrieved {len(results)} documents")
                for j, result in enumerate(results):
                    preview = result[:150].replace('\n', ' ') + "..."
                    logger.info(f"  Result {j+1}: {preview}")
            else:
                logger.warning("No results retrieved")

        logger.info("\nRAG testing completed successfully")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

    return True


def main():
    """Main function with improved error handling and status reporting"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="RAG Index Builder")
    parser.add_argument("action", choices=["build", "load", "test", "rebuild", "status"],
                       help="Action to perform")
    parser.add_argument("--force", action="store_true",
                       help="Force rebuild even if index exists")
    parser.add_argument("--quiet", action="store_true",
                       help="Reduce output verbosity")

    args = parser.parse_args()

    # Configure logging
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    else:
        logging.getLogger().setLevel(logging.INFO)

    try:
        if args.action == "build":
            if not args.force and vector_store.load():
                logger.info("Index already exists - use --force to rebuild or 'rebuild' action")
                return 0
            success = build_index()
            if success and not args.quiet:
                test_index()
            return 0 if success else 1

        elif args.action == "load":
            success = load_index()
            if success:
                stats = vector_store.get_stats()
                logger.info(f"Index loaded successfully: {stats}")
            return 0 if success else 1

        elif args.action == "test":
            if not load_index():
                logger.info("Index not found, building for testing...")
                if not build_index():
                    logger.error("Failed to build index for testing")
                    return 1
            test_index()
            return 0

        elif args.action == "rebuild":
            logger.info("Rebuilding index...")
            vector_store = VectorStore()  # Fresh instance
            success = build_index()
            return 0 if success else 1

        elif args.action == "status":
            show_status()
            return 0

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


def show_status():
    """Show current RAG system status"""
    from .embeddings import is_available, cache_stats

    print("RAG System Status")
    print("=" * 50)

    # Embeddings status
    emb_available = is_available()
    print(f"Embeddings API: {'✅ Available' if emb_available else '❌ Unavailable'}")

    # Cache status
    cache_info = cache_stats()
    print(f"Cache: {cache_info['cached_entries']} entries ({cache_info['estimated_memory_bytes']:,} bytes)")

    # Vector store status
    vs_loaded = vector_store.load()
    if vs_loaded:
        stats = vector_store.get_stats()
        print(f"Vector Store: ✅ Loaded ({stats['total_documents']} documents)")
        print(f"  Dimensions: {stats['vector_dimension']}")
    else:
        print("Vector Store: ❌ Not loaded")

    # Medical KB status
    try:
        from .medical_kb import MEDICAL_DOCUMENTS
        print(f"Medical KB: ✅ Loaded ({len(MEDICAL_DOCUMENTS)} documents)")
        categories = list(set(doc["category"] for doc in MEDICAL_DOCUMENTS))
        print(f"  Categories: {', '.join(sorted(categories))}")
    except Exception as e:
        print(f"Medical KB: ❌ Error loading ({e})")

    print("\nTo build index: python -m app.rag.build_index build")
    print("To test system: python -m app.rag.build_index test")


if __name__ == "__main__":
    main()