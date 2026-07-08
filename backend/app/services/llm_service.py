import openai
from typing import List, Dict, Any, AsyncGenerator, Optional
import os
from dotenv import load_dotenv
import logging
import json
from datetime import datetime

# Load env
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI client (with fallback)
api_key = os.getenv("OPENAI_API_KEY")
if api_key and not ("your-" in api_key.lower() or "here" in api_key.lower()):
    try:
        client = openai.AsyncOpenAI(api_key=api_key)
        logger.info("OpenAI client initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenAI client: {e}")
        client = None
else:
    client = None
    if api_key and ("your-" in api_key.lower() or "here" in api_key.lower()):
        logger.warning("OpenAI API key appears to be placeholder - using fallback responses")
    else:
        logger.warning("OpenAI API key not found - LLM service will use fallback responses")


class LLMService:
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.session_history: Dict[str, List[Dict]] = {}

    # --------------------------------------------------
    # MAIN CHAT FUNCTION (UPGRADED)
    # --------------------------------------------------
    async def get_chat_response(
        self,
        message_history: List[Dict],
        session_id: Optional[str] = None,
        structured: bool = False
    ) -> Any:
        """
        Get chat response from LLM
        If structured=True → returns JSON
        """

        # Check if client is available
        if not client:
            logger.info("OpenAI client not available - using fallback response")
            fallback = self._get_fallback_response(message_history)
            if session_id:
                await self._update_session_history(session_id, message_history, fallback)
            return fallback

        try:
            system_prompt = self._get_advanced_healthcare_prompt(structured)

            messages = [{"role": "system", "content": system_prompt}] + message_history

            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.5,  # lower = more reliable
                max_tokens=1000
            )

            content = response.choices[0].message.content

            # Try parsing JSON if structured
            if structured:
                try:
                    content = json.loads(content)
                except:
                    logger.warning("Failed to parse structured JSON response")

            if session_id:
                await self._update_session_history(session_id, message_history, content)

            return content

        except Exception as e:
            logger.error(f"LLM error: {str(e)}")
            fallback = self._get_fallback_response(message_history)
            if session_id:
                await self._update_session_history(session_id, message_history, fallback)
            return fallback

    # --------------------------------------------------
    # STREAMING (UNCHANGED BUT CLEANED)
    # --------------------------------------------------
    async def stream_response(
        self,
        message_history: List[Dict]
    ) -> AsyncGenerator[str, None]:

        # Check if client is available
        if not client:
            logger.info("OpenAI client not available - using fallback streaming response")
            yield "⚠️ I'm having trouble responding right now. Please try again later."
            return

        try:
            system_prompt = self._get_advanced_healthcare_prompt()

            messages = [{"role": "system", "content": system_prompt}] + message_history

            stream = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.5,
                max_tokens=1000,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            yield "⚠️ I'm having trouble responding right now."

    # --------------------------------------------------
    # SESSION MEMORY
    # --------------------------------------------------
    async def get_session_history(self, session_id: str) -> List[Dict]:
        return self.session_history.get(session_id, [])

    async def _update_session_history(
        self,
        session_id: str,
        messages: List[Dict],
        response: Any
    ):
        if session_id not in self.session_history:
            self.session_history[session_id] = []

        self.session_history[session_id].extend(messages)

        self.session_history[session_id].append({
            "role": "assistant",
            "content": str(response),
            "timestamp": datetime.now().isoformat()
        })

        # keep last 50
        self.session_history[session_id] = self.session_history[session_id][-50:]

    # --------------------------------------------------
    # 🔥 ADVANCED PROMPT (CORE UPGRADE)
    # --------------------------------------------------
    def _get_advanced_healthcare_prompt(self, structured: bool = False) -> str:

        if structured:
            return """
You are an AI medical assistant.

Analyze the user's symptoms and return ONLY valid JSON.

Format:
{
  "symptoms": [],
  "possible_conditions": [],
  "severity": "low | medium | high",
  "advice": [],
  "recommended_specialist": "",
  "urgency": "normal | urgent | emergency",
  "follow_up_questions": []
}

Rules:
- Do NOT give diagnosis
- Do NOT prescribe medicine
- Keep results realistic and safe
- If emergency symptoms → urgency = "emergency"
"""

        return """
You are Dr. CareCompanion, a professional AI medical assistant.

Your approach:
1. FIRST, acknowledge the patient's concern empathetically
2. Ask ONE focused follow-up question at a time to gather more information
3. Confirm understanding of symptoms before proceeding
4. Take a step-by-step diagnostic approach
5. Never rush to conclusions or diagnoses

CONVERSATIONAL STYLE:
- Be warm, professional, and reassuring like a real doctor
- Use phrases like "I understand...", "Let me ask you...", "To help me understand better..."
- Ask about: duration, severity, triggers, associated symptoms, medical history
- Progress logically: symptoms → context → possible considerations → recommendations

RESPONSE STRUCTURE:
1. Acknowledge: Show you understand their concern
2. Clarify: Ask ONE specific follow-up question
3. Summarize: Briefly restate what you understand so far
4. Next Step: Explain what information you need next

IMPORTANT:
- Ask only ONE question per response
- Wait for their answer before proceeding
- If symptoms suggest emergency, advise seeking immediate help
- Always maintain professional medical boundaries

Example flow:
Patient: "I have a headache"
You: "I understand headaches can be concerning. How long have you had this headache, and can you describe the pain - is it throbbing, constant, or does it come and go?"
"""

    # --------------------------------------------------
    # FALLBACK
    # --------------------------------------------------
    def _get_fallback_response(self, message_history: List[Dict]) -> str:

        last_msg = message_history[-1]["content"].lower() if message_history else ""

        if any(x in last_msg for x in ["chest pain", "breathing", "unconscious"]):
            return "⚠️ This may be an emergency. Please seek immediate medical attention."

        return "⚠️ I'm having trouble responding. Please try again or consult a doctor."


# Global instance
llm_service = LLMService()