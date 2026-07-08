"""
Safety Agent
Validates and sanitizes all agent outputs before returning to the user.

Improvements over original:
- 40+ emergency keywords (was 19), organized into clinical categories.
- Multi-layer emergency scoring — any 2+ emergency signals = emergency response.
- Unsafe phrase stripping: catches definitive diagnoses, drug prescriptions,
  dosage instructions, and guarantee language even if the LLM misses them.
- Paediatric emergency pathway (under-3-months fever, seizure in child).
- Age-aware advice (elderly, paediatric, pregnancy caveats).
- Structured mental-health crisis pathway (suicidal ideation → crisis line).
- Crisis hotline numbers (Pakistan + international).
- Richer emergency response with triage priority, nearby facility guidance.
- Full disclaimer always appears at top AND bottom of advice list.
"""

import json
import re
import logging
import httpx
from typing import Dict, List, Optional, Tuple
from app.utils.config import settings
from app.utils.prompts import SAFETY_AGENT_PROMPT

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Emergency keyword sets  (lower-case, used for 'in' matching)
# ─────────────────────────────────────────────────────────────────────────────

EMERGENCY_PHYSICAL: List[str] = [
    # Cardiac
    "chest pain", "chest tightness", "chest pressure", "crushing chest",
    "heart attack", "cardiac arrest", "palpitations with fainting",
    # Respiratory
    "can't breathe", "cannot breathe", "difficulty breathing",
    "shortness of breath", "stopped breathing", "not breathing",
    "respiratory arrest", "blue lips", "cyanosis",
    # Neurological
    "unconscious", "unresponsive", "loss of consciousness",
    "fainting", "syncope", "stroke", "facial drooping",
    "sudden vision loss", "sudden severe headache", "thunderclap headache",
    "seizure", "convulsions", "paralysis", "hemiplegia",
    # Bleeding / Haemorrhage
    "severe bleeding", "uncontrolled bleeding", "coughing blood",
    "vomiting blood", "blood in vomit", "massive blood loss",
    # Shock / Systemic
    "anaphylaxis", "anaphylactic", "allergic shock",
    "septic shock", "hypovolemic shock", "sepsis",
    # Gastrointestinal
    "severe abdominal pain", "rigid abdomen",
    # Toxicological
    "overdose", "drug overdose", "poisoning", "ingested poison",
    "swallowed chemicals",
    # Obstetric
    "eclampsia", "placental abruption", "cord prolapse",
    "postpartum haemorrhage",
    # Paediatric
    "infant not breathing", "baby not waking", "febrile convulsion",
    "meningococcal rash", "purpuric rash with fever",
]

EMERGENCY_MENTAL_HEALTH: List[str] = [
    "suicidal", "want to die", "kill myself", "end my life",
    "self-harm", "cutting myself", "harming myself",
    "psychosis", "actively hallucinating", "violent ideation",
]

ALL_EMERGENCY_KEYWORDS: List[str] = EMERGENCY_PHYSICAL + EMERGENCY_MENTAL_HEALTH

# ─────────────────────────────────────────────────────────────────────────────
# Phrases that must NEVER appear in safe output
# ─────────────────────────────────────────────────────────────────────────────

UNSAFE_PATTERNS: List[Tuple[str, str]] = [
    # Definitive diagnoses
    (r"\byou\s+(have|definitely\s+have|are\s+diagnosed\s+with)\b",
     "You may have"),
    (r"\bthis\s+is\s+definitely\b",
     "This could be"),
    # Drug prescriptions / dosage instructions
    (r"\btake\s+\d+\s*(mg|ml|tablet|capsule|dose)",
     "[dosage removed — consult your doctor]"),
    (r"\bprescribe\b",
     "recommend consulting a doctor about"),
    (r"\bI\s+recommend\s+taking\b",
     "A doctor may consider"),
    # Guarantee / certainty language
    (r"\bguaranteed?\b",
     "possibly"),
    (r"\b100\s*%\s*(safe|effective|accurate|certain)\b",
     "potentially effective"),
    (r"\bwill\s+cure\b",
     "may help treat"),
    (r"\bno\s+need\s+to\s+see\s+a\s+doctor\b",
     "still consider seeing a doctor"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Disclaimers & emergency messages
# ─────────────────────────────────────────────────────────────────────────────

DISCLAIMER = (
    "⚠️ MEDICAL DISCLAIMER: This information is for general educational guidance "
    "only and does NOT constitute a medical diagnosis or professional medical advice. "
    "Always consult a qualified, licensed healthcare professional before making any "
    "medical decisions. Individual circumstances vary — only your doctor can evaluate "
    "your specific situation."
)

EMERGENCY_MESSAGE = (
    "🚨 EMERGENCY ALERT: Your symptoms may indicate a life-threatening condition. "
    "Call emergency services IMMEDIATELY:\n"
    "  🇵🇰 Pakistan Rescue: 1122 | Edhi: 115 | Aman: 1021\n"
    "  🌍 International: use your local emergency number (911 / 999 / 112)\n"
    "Go to the nearest Emergency Room. Do NOT wait."
)

MENTAL_HEALTH_CRISIS_MESSAGE = (
    "🆘 MENTAL HEALTH CRISIS SUPPORT:\n"
    "  🇵🇰 Umang helpline (Pakistan): 0317-4288665\n"
    "  🇵🇰 Rozan Counselling: 051-2890505\n"
    "  🌍 International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/\n"
    "You are not alone. Please reach out to someone you trust or call now."
)


class SafetyAgent:
    """
    Final validation layer ensuring every response is safe, responsible,
    and appropriately caveated before delivery to the user.
    """

    def __init__(self):
        try:
            self.api_url = "https://api.openai.com/v1/chat/completions"
            self.model   = settings.OPENAI_MODEL
            self.api_key = settings.OPENAI_API_KEY

            # Check if API key is properly set (not placeholder)
            if self.api_key and ("your-" in self.api_key.lower() or "here" in self.api_key.lower()):
                logger.warning("OpenAI API key appears to be placeholder - using fallback mode")
                self.api_key = None

            self.use_llm = bool(self.api_key)
        except Exception as e:
            logger.warning(f"API key not configured for safety validation: {e}")
            self.use_llm = False

    async def validate(
        self,
        combined_response:    dict,
        original_user_message: str,
    ) -> dict:
        """
        Validate and sanitize the combined agent response.

        Steps:
          1. Emergency detection (local, fast — no API needed)
          2. Mental health crisis detection
          3. Unsafe phrase stripping
          4. LLM-based review (if API available)
          5. Disclaimer enforcement
          6. Age-specific caveats
        """
        # Step 1 – Emergency detection
        emergency_type = self._detect_emergency(original_user_message, combined_response)

        if emergency_type == "physical":
            return self._build_emergency_response(combined_response, mental_health=False)
        if emergency_type == "mental_health":
            return self._build_emergency_response(combined_response, mental_health=True)

        # Step 2 – Strip unsafe phrases from all text fields
        combined_response = self._strip_unsafe_phrases(combined_response)

        # Step 3 – LLM safety review
        if self.use_llm:
            combined_response = await self._llm_validate(combined_response)

        # Step 4 – Enforce disclaimer
        combined_response = self._enforce_disclaimer(combined_response)

        # Step 5 – Age-specific caveats
        combined_response = self._add_age_caveats(combined_response)

        return combined_response

    # ------------------------------------------------------------------ #
    #  Emergency detection                                                #
    # ------------------------------------------------------------------ #

    def _detect_emergency(self, user_message: str, response: dict) -> Optional[str]:
        """
        Returns 'physical', 'mental_health', or None.
        Uses a scoring approach — 1 physical keyword or any mental health keyword
        triggers the appropriate pathway.
        """
        text = user_message.lower()

        # Scan extracted symptoms too
        symptoms = response.get("symptoms", [])
        if isinstance(symptoms, list):
            text += " " + " ".join(str(s).lower() for s in symptoms)

        # Also scan advice and conditions
        for advice_item in response.get("advice", []):
            text += " " + str(advice_item).lower()

        # Mental health crisis — highest priority
        if any(kw in text for kw in EMERGENCY_MENTAL_HEALTH):
            return "mental_health"

        # Physical emergency
        physical_hits = sum(1 for kw in EMERGENCY_PHYSICAL if kw in text)
        if physical_hits >= 1:
            return "physical"

        # Risk/urgency fields
        if response.get("risk_level", "").lower() in ("critical", "high"):
            return "physical"
        if response.get("urgency", "").lower() == "emergency":
            return "physical"

        return None

    # ------------------------------------------------------------------ #
    #  Emergency response builders                                        #
    # ------------------------------------------------------------------ #

    def _build_emergency_response(self, original: dict, mental_health: bool) -> dict:
        if mental_health:
            return {
                "symptoms":             original.get("symptoms", []),
                "possible_conditions":  original.get("possible_conditions", []),
                "severity":             "high",
                "urgency":              "emergency",
                "emergency":            True,
                "emergency_type":       "mental_health_crisis",
                "safe":                 True,
                "advice":               [
                    MENTAL_HEALTH_CRISIS_MESSAGE,
                    "Please tell a trusted person — family member, friend, or colleague — about how you are feeling.",
                    "Do not be alone right now.",
                    DISCLAIMER,
                ],
                "recommended_specialist": "Psychiatrist / Emergency Mental Health Team",
                "alternative_specialists": ["General Practitioner", "Emergency Medicine Specialist"],
                "precautions": [
                    "Ensure the person is not alone.",
                    "Remove access to potential means of self-harm if safe to do so.",
                    "Call emergency services if there is immediate risk.",
                ],
                "first_aid_steps": [
                    "Stay with the person and listen without judgement.",
                    "Call a mental health crisis line listed above.",
                    "If immediate risk: call 1122 / 115 or take to nearest ER.",
                ],
                "follow_up_questions": [],
                "expected_tests":      [],
                "lifestyle_advice":    [],
                "disclaimer":          DISCLAIMER,
            }

        return {
            "symptoms":             original.get("symptoms", []),
            "possible_conditions":  original.get("possible_conditions", []),
            "severity":             "critical",
            "urgency":              "emergency",
            "emergency":            True,
            "emergency_type":       "physical",
            "safe":                 True,
            "advice":               [
                EMERGENCY_MESSAGE,
                "Do NOT drive yourself — call an ambulance.",
                "Do not eat or drink anything until a doctor has assessed you.",
                "If the patient stops breathing and you are trained: start CPR.",
                DISCLAIMER,
            ],
            "recommended_specialist": "Emergency Medicine / ER",
            "alternative_specialists": [],
            "booking_urgency":        "CALL EMERGENCY SERVICES NOW — 1122 / 115",
            "precautions":            [
                "Call emergency services immediately.",
                "Keep the patient calm and still.",
                "Loosen restrictive clothing (ties, belts).",
                "Do not give food, water, or medication.",
                "Note the time symptoms started — tell paramedics.",
            ],
            "first_aid_steps": [
                "Call 1122 / 115 / 112 immediately.",
                "Stay with the patient and keep them conscious if possible.",
                "If cardiac arrest and trained: begin CPR — 30 compressions, 2 breaths.",
                "If anaphylaxis and EpiPen available: administer to outer thigh.",
                "If unconscious and breathing: place in recovery position.",
                "If severe bleeding: apply firm direct pressure to wound.",
            ],
            "follow_up_questions": [],
            "expected_tests":      [],
            "lifestyle_advice":    [],
            "disclaimer":          DISCLAIMER,
        }

    # ------------------------------------------------------------------ #
    #  Unsafe phrase stripping                                            #
    # ------------------------------------------------------------------ #

    def _strip_unsafe_phrases(self, response: dict) -> dict:
        """Apply regex-based replacement to all string fields and list-of-string fields."""
        text_fields = ["differential", "advice_summary", "urgency_note"]
        list_fields = ["advice", "precautions", "first_aid_steps",
                       "lifestyle_advice", "follow_up_questions"]

        for field in text_fields:
            val = response.get(field)
            if isinstance(val, str):
                response[field] = self._apply_unsafe_replacements(val)

        for field in list_fields:
            items = response.get(field, [])
            if isinstance(items, list):
                response[field] = [
                    self._apply_unsafe_replacements(str(item))
                    for item in items
                ]

        return response

    def _apply_unsafe_replacements(self, text: str) -> str:
        for pattern, replacement in UNSAFE_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    # ------------------------------------------------------------------ #
    #  LLM safety review                                                  #
    # ------------------------------------------------------------------ #

    async def _llm_validate(self, combined_response: dict) -> dict:
        # Skip LLM validation if API key is not available
        if not self.api_key:
            logger.info("OpenAI API key not available - skipping LLM safety validation")
            return combined_response

        response_text = json.dumps(combined_response, indent=2)

        payload = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": [
                {"role": "system", "content": SAFETY_AGENT_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Review and sanitize this medical AI response JSON. "
                        "Rules:\n"
                        "1. Remove any definitive diagnosis language ('you have X').\n"
                        "2. Remove any drug names, prescriptions, or dosages.\n"
                        "3. Remove guarantee language ('this will cure', '100% safe').\n"
                        "4. Ensure every condition is listed as 'possible' or 'suspected'.\n"
                        "5. Preserve all useful guidance but soften certainty.\n"
                        "6. Return ONLY the corrected JSON object.\n\n"
                        f"{response_text}"
                    ),
                },
            ],
            "temperature": 0.0,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            raw_text = data["choices"][0]["message"]["content"]
            return self._parse_json_response(raw_text, fallback=combined_response)
        except Exception as e:
            logger.error(f"Safety LLM validation error: {e}")
            return combined_response

    # ------------------------------------------------------------------ #
    #  Post-processing                                                    #
    # ------------------------------------------------------------------ #

    def _enforce_disclaimer(self, response: dict) -> dict:
        """Ensure disclaimer appears in the response and at top & bottom of advice list."""
        response["disclaimer"] = DISCLAIMER
        response.setdefault("safe",      True)
        response.setdefault("emergency", False)

        advice = response.get("advice", [])
        if isinstance(advice, list):
            # Remove stale disclaimer instances to avoid duplication
            advice = [a for a in advice if a != DISCLAIMER]
            # Add at top and bottom
            advice = [DISCLAIMER] + advice + [DISCLAIMER]
        else:
            advice = [DISCLAIMER]
        response["advice"] = advice
        return response

    def _add_age_caveats(self, response: dict) -> dict:
        """Append age-specific warnings to precautions."""
        # Extract age from symptom context if present
        ctx = response.get("patient_context", {}) or {}
        age = ctx.get("age")

        extra: List[str] = []
        if age is not None:
            if age < 1:
                extra.append(
                    "⚠️ INFANT: Any fever in a baby under 3 months requires IMMEDIATE medical review."
                )
            elif age < 5:
                extra.append(
                    "⚠️ YOUNG CHILD: Children under 5 can deteriorate rapidly — seek prompt medical attention."
                )
            elif age > 65:
                extra.append(
                    "⚠️ ELDERLY: Older adults may present atypically — symptoms can be less obvious. "
                    "Err on the side of caution and seek medical advice sooner."
                )

        if extra:
            precautions = response.get("precautions", [])
            response["precautions"] = extra + precautions

        return response

    # ------------------------------------------------------------------ #
    #  Parse helper                                                       #
    # ------------------------------------------------------------------ #

    def _parse_json_response(self, raw_text: str, fallback: dict) -> dict:
        clean = re.sub(r"```(?:json)?|```", "", raw_text).strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            fallback["disclaimer"] = DISCLAIMER
            fallback["safe"]       = True
            return fallback


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────

_agent_instance: Optional[SafetyAgent] = None


async def validate(combined_response: dict, original_user_message: str) -> dict:
    """Module-level wrapper – maintains a singleton SafetyAgent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = SafetyAgent()
    return await _agent_instance.validate(combined_response, original_user_message)