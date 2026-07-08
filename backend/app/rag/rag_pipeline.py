from typing import List, Optional
import logging
from app.services.llm_service import llm_service
from .retriever import retrieve_context

logger = logging.getLogger(__name__)


async def generate_rag_response(user_query: str, k: int = 3) -> str:
    """
    Main RAG pipeline for medical queries:
    1. Retrieve relevant medical context
    2. Generate informative response using retrieved knowledge
    3. Handle errors gracefully with fallbacks

    Args:
        user_query: The user's medical question
        k: Number of documents to retrieve

    Returns:
        Formatted medical information response
    """

    try:
        # Input validation
        if not user_query or not user_query.strip():
            logger.warning("Empty user query provided to RAG")
            return "Please provide a medical question or concern."

        user_query = user_query.strip()

        # Step 1: Retrieve relevant medical documents
        logger.info(f"Retrieving context for query: {user_query[:50]}...")
        retrieved_docs = retrieve_context(user_query, k=k)

        # Step 2: Validate retrieved content
        if not retrieved_docs:
            logger.warning("No documents retrieved from RAG system")
            return await _generate_fallback_response(user_query)

        # Check for meaningful content (not just error messages)
        meaningful_docs = [doc for doc in retrieved_docs if len(doc) > 100 and "unavailable" not in doc.lower()]
        if not meaningful_docs:
            logger.warning("Retrieved documents contain no meaningful medical content")
            return await _generate_fallback_response(user_query)

        logger.info(f"Using {len(meaningful_docs)} meaningful documents for RAG response")

        # Step 3: Generate informative response
        return _generate_informative_response(user_query, meaningful_docs)

    except Exception as e:
        logger.error(f"RAG pipeline error: {e}")
        return await _generate_fallback_response(user_query)


def _build_rag_system_prompt(context: str) -> str:
    """Build the RAG system prompt with medical context and conversational approach"""
    return f"""You are Dr. CareCompanion, a professional AI medical assistant with access to verified medical information.

Use the provided medical context to inform your response, but always prioritize safety and a step-by-step diagnostic approach.

MEDICAL CONTEXT:
{context}

CONVERSATIONAL APPROACH:
1. Acknowledge the patient's concern empathetically
2. Ask ONE focused follow-up question at a time
3. Take a methodical, doctor-like approach
4. Don't rush to conclusions

RESPONSE GUIDELINES:
- Be warm, professional, and reassuring like a real doctor
- Use phrases like "I understand...", "Let me ask you...", "To help me understand better..."
- Ask about: duration, severity, triggers, associated symptoms, medical history
- Progress logically through the diagnostic process
- Provide general educational information when appropriate
- Always recommend consulting qualified healthcare professionals

SAFETY RULES:
- Never prescribe medications or dosages
- Never suggest stopping prescribed medications
- Never give treatment advice for serious conditions
- Flag emergency symptoms immediately
- Always err on the side of caution

If you cannot answer based on the provided context, respond with: "Based on available medical information, I recommend consulting a healthcare professional for personalized advice on this matter.\""""


def _generate_context_response(user_query: str, context_docs: List[str]) -> str:
    """Generate a conversational response from retrieved context"""
    try:
        # Extract key information from the first relevant document
        context = context_docs[0][:800]  # Limit context length

        # Extract the title to understand what we're dealing with
        lines = context.split('\n')
        title = "this condition"  # default
        for line in lines[:5]:  # Check first few lines for title
            if line.strip() and not line.startswith(' '):
                title = line.strip()
                break

        # Create a conversational, doctor-like response
        response = f"I understand you're asking about {user_query.lower()}. Based on medical information about {title.lower()}, "

        # Extract key points from context for conversational response
        if "symptoms" in context.lower():
            response += "there are several symptoms that can be associated with this. "
        elif "causes" in context.lower():
            response += "there are various factors that can contribute to this. "
        elif "emergency" in context.lower():
            response += "this can sometimes indicate a serious situation. "
        else:
            response += "I have some general information that might be helpful. "

        response += "\n\nTo better assist you, could you tell me:\n"
        response += "- How long have you been experiencing these symptoms?\n"
        response += "- Are there any other symptoms you've noticed?\n"
        response += "- Have you had similar issues before?\n\n"

        response += "⚠️ Remember, I'm here to provide general information. Please consult a healthcare professional for personalized medical advice."

        return response
    except Exception as e:
        logger.error(f"Context response generation failed: {e}")
        return "I understand your concern. To help me provide better guidance, could you tell me more about your symptoms and how long you've been experiencing them? Please consult a healthcare professional for personalized medical advice."


def _generate_informative_response(user_query: str, context_docs: List[str]) -> str:
    """Generate an informative response directly from retrieved medical context"""
    try:
        if not context_docs:
            return "I don't have specific medical information about that topic. Please consult a healthcare professional for personalized advice."

        # Use the most relevant document
        context = context_docs[0]

        # Extract title and content
        lines = context.split('\n')
        title = ""
        content_start = 0

        for i, line in enumerate(lines):
            if line.strip() and not line.startswith(' ') and not line.startswith('Content:'):
                title = line.strip()
                content_start = i + 1
                break

        # Get the main content
        main_content = '\n'.join(lines[content_start:])

        # Format as informative medical response
        response = f"**{title}**\n\n"

        # Add the medical information
        response += main_content[:1500]  # Limit length for readability

        if len(main_content) > 1500:
            response += "\n\n[...content continues...]"

        # Add safety disclaimer
        response += "\n\n---\n"
        response += "⚠️ **Important:** This is general medical information for educational purposes only. "
        response += "It is not a substitute for professional medical advice, diagnosis, or treatment. "
        response += "Please consult a qualified healthcare professional for your specific health concerns."

        return response

    except Exception as e:
        logger.error(f"Informative response generation failed: {e}")
        return "I have medical information available but encountered an issue displaying it. Please consult a healthcare professional for personalized medical advice."


async def _generate_fallback_response(user_query: str) -> str:
    """Generate a safe fallback response when RAG fails"""
    fallback_messages = [
        {
            "role": "system",
            "content": """You are a medical assistant AI.

Since I cannot access medical knowledge at this moment, provide a general, safe response.

Rules:
- Do NOT give specific medical advice
- Always recommend seeing a doctor
- Be empathetic and supportive
- Focus on general wellness"""
        },
        {
            "role": "user",
            "content": user_query
        }
    ]

    try:
        return await llm_service.get_chat_response(fallback_messages)
    except Exception as e:
        logger.error(f"Fallback response failed: {e}")
        return ("I'm currently experiencing technical difficulties. "
                "Please consult a qualified healthcare professional for medical advice.")


def get_rag_status() -> dict:
    """Get RAG system status"""
    from .retriever import get_retrieval_stats
    return {
        "rag_system": "active",
        "retrieval_stats": get_retrieval_stats(),
        "pipeline_status": "ready"
    }