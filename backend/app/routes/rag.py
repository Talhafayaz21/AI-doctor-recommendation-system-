from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from app.rag.rag_pipeline import generate_rag_response, get_rag_status
from app.rag.retriever import retrieve_context, get_retrieval_stats
from app.rag.medical_kb import MEDICAL_DOCUMENTS, get_documents_by_category

router = APIRouter()

logger = logging.getLogger(__name__)

class RAGQuery(BaseModel):
    query: str
    k: Optional[int] = 3

class RAGResponse(BaseModel):
    response: str
    retrieved_documents: List[str]
    timestamp: str

class MedicalSearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    limit: Optional[int] = 10


@router.post("/query", response_model=RAGResponse)
async def rag_query(request: RAGQuery):
    """Generate RAG response for medical query"""
    try:
        # Input validation
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        if request.k < 1 or request.k > 10:
            raise HTTPException(status_code=400, detail="k must be between 1 and 10")

        logger.info(f"RAG query: '{request.query[:100]}...' (k={request.k})")

        # Generate RAG response
        response = await generate_rag_response(request.query, k=request.k)

        # Also get retrieved documents for transparency
        retrieved_docs = retrieve_context(request.query, k=request.k)

        # Validate response
        if not response or not response.strip():
            logger.warning("RAG generated empty response")
            response = "I'm sorry, I couldn't find specific medical information for your query. Please consult a healthcare professional for personalized advice."

        return RAGResponse(
            response=response,
            retrieved_documents=retrieved_docs,
            timestamp="2026-05-07T13:35:00Z"  # Updated timestamp
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG query error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error processing RAG query")


@router.post("/search")
async def search_medical_kb(request: MedicalSearchRequest):
    """Search medical knowledge base"""
    try:
        # If category specified, filter by category
        if request.category:
            docs = get_documents_by_category(request.category)
        else:
            docs = MEDICAL_DOCUMENTS

        # Simple keyword search
        query_lower = request.query.lower()
        results = []

        for doc in docs:
            if (query_lower in doc["title"].lower() or
                query_lower in doc["content"].lower()):
                results.append({
                    "title": doc["title"],
                    "category": doc["category"],
                    "snippet": doc["content"][:300] + "..." if len(doc["content"]) > 300 else doc["content"]
                })

        return {
            "query": request.query,
            "category": request.category,
            "results": results[:request.limit],
            "total_found": len(results)
        }

    except Exception as e:
        logger.error(f"Medical search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/categories")
async def get_medical_categories():
    """Get available medical categories"""
    categories = list(set(doc["category"] for doc in MEDICAL_DOCUMENTS))
    return {"categories": sorted(categories)}


@router.get("/documents")
async def get_medical_documents(category: Optional[str] = None, limit: int = 50):
    """Get medical documents"""
    try:
        if category:
            docs = get_documents_by_category(category)
        else:
            docs = MEDICAL_DOCUMENTS

        # Return basic info without full content for performance
        result = []
        for doc in docs[:limit]:
            result.append({
                "title": doc["title"],
                "category": doc["category"],
                "word_count": len(doc["content"].split())
            })

        return {
            "documents": result,
            "total": len(docs),
            "category": category
        }

    except Exception as e:
        logger.error(f"Document retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve documents: {str(e)}")


@router.get("/status")
async def rag_system_status():
    """Get RAG system status"""
    try:
        return get_rag_status()
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return {
            "rag_system": "error",
            "error": str(e)
        }


@router.get("/retrieval-stats")
async def retrieval_stats():
    """Get retrieval system statistics"""
    try:
        return get_retrieval_stats()
    except Exception as e:
        logger.error(f"Stats retrieval error: {e}")
        return {
            "error": str(e)
        }