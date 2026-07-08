from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
#  FASTAPI ROUTER
# ─────────────────────────────────────────────────────────────

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    message_history: List[Dict] = []
    orchestrator_result: dict = {}


class ChatResponse(BaseModel):
    response: str


@router.post("/conversation", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint. Accepts a user message + history,
    returns the next conversational response.
    """
    try:
        full_history = request.message_history + [
            {"role": "user", "content": request.message}
        ]

        response = await _generate_conversational_response(
            message_history=full_history,
            last_user_message=request.message,
            orchestrator_result=request.orchestrator_result,
        )

        return ChatResponse(response=response)

    except Exception as exc:
        logger.exception("Chat endpoint error: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


# ─────────────────────────────────────────────────────────────
#  ENUMS & DATA CLASSES
# ─────────────────────────────────────────────────────────────

class ConversationStage(Enum):
    EMERGENCY        = auto()   # bypass everything — direct to ER
    INITIAL_COLLECT  = auto()   # first message, identify symptoms
    DEEPEN_SYMPTOMS  = auto()   # ask targeted follow-up questions
    GATHER_CONTEXT   = auto()   # medical history, medications
    DELIVER_REPORT   = auto()   # full assessment + doctor list


class RiskLevel(Enum):
    LOW      = "low"
    MODERATE = "moderate"
    HIGH     = "high"
    CRITICAL = "critical"


@dataclass
class ConversationState:
    """
    Derived from message history on every call.
    Single source of truth for what the user has/hasn't told us.
    """
    stage: ConversationStage = ConversationStage.INITIAL_COLLECT

    symptoms: List[str] = field(default_factory=list)
    duration_known: bool = False
    severity_known: bool = False
    history_known: bool = False
    medications_known: bool = False
    location: Optional[str] = None

    risk_level: RiskLevel = RiskLevel.LOW
    urgency: str = "routine"
    conditions: List[Dict] = field(default_factory=list)
    specialist: str = "General Practitioner"
    precautions: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────
#  EMERGENCY SYMPTOM DETECTION
# ─────────────────────────────────────────────────────────────

EMERGENCY_PATTERNS: List[Tuple[str, str]] = [
    (r"\bchest\s+pain\b",              "chest pain"),
    (r"\bcan.?t\s+breath",             "breathing difficulty"),
    (r"\bshortness\s+of\s+breath\b",   "shortness of breath"),
    (r"\bstroke\b",                    "stroke symptoms"),
    (r"\bface\s+droop",                "facial drooping"),
    (r"\barm\s+weak",                  "arm weakness"),
    (r"\bspeech\s+slur",               "slurred speech"),
    (r"\bseizure\b",                   "seizure"),
    (r"\bunconscious\b",               "loss of consciousness"),
    (r"\bbleed(ing)?\s+(heavily|profuse|uncontrolled)", "severe bleeding"),
    (r"\boverdos",                     "overdose"),
    (r"\bsuicid",                      "suicidal ideation"),
    (r"\bsever(e)?\s+allerg",          "severe allergic reaction"),
    (r"\banaphylax",                   "anaphylaxis"),
]


def _detect_emergency(text: str) -> Optional[str]:
    lowered = text.lower()
    for pattern, label in EMERGENCY_PATTERNS:
        if re.search(pattern, lowered):
            return label
    return None


# ─────────────────────────────────────────────────────────────
#  CONVERSATION ANALYSER
# ─────────────────────────────────────────────────────────────

def _extract_location(messages: List[Dict]) -> Optional[str]:
    known_cities = {
        "islamabad", "rawalpindi", "lahore", "karachi",
        "peshawar", "quetta", "faisalabad", "multan",
    }
    for msg in messages:
        if msg.get("role") != "user":
            continue
        words = msg.get("content", "").lower().split()
        for word in words:
            clean = re.sub(r"[^a-z]", "", word)
            if clean in known_cities:
                return clean.capitalize()
    return None


def _user_has_answered(messages: List[Dict], *keywords: str) -> bool:
    user_text = " ".join(
        m.get("content", "").lower()
        for m in messages
        if m.get("role") == "user"
    )
    return any(kw.lower() in user_text for kw in keywords)


def _analyse_conversation(
    message_history: List[Dict],
    orchestrator_result: dict,
) -> ConversationState:
    state = ConversationState()

    symptoms_data  = orchestrator_result.get("symptoms", {})
    state.symptoms = symptoms_data.get("symptoms", [])

    diag = orchestrator_result.get("diagnosis", {})
    recs = orchestrator_result.get("recommendations", {})

    raw_conditions = diag.get("conditions", [])
    state.conditions = [
        c for c in raw_conditions
        if str(c.get("probability", 0)).lower() != "nan"
        and float(c.get("probability", 0)) > 0
    ]

    risk_raw         = diag.get("risk_level", "low").lower()
    state.risk_level = RiskLevel(risk_raw) if risk_raw in RiskLevel._value2member_map_ else RiskLevel.LOW
    state.urgency    = diag.get("urgency", "routine")
    state.specialist = recs.get("recommended_specialist", "General Practitioner")
    state.precautions = recs.get("precautions", [])

    state.location          = _extract_location(message_history)
    state.duration_known    = _user_has_answered(message_history, "day", "days", "hour", "hours", "week", "month")
    state.severity_known    = _user_has_answered(message_history, *[str(i) for i in range(1, 11)], "mild", "moderate", "severe")
    state.history_known     = _user_has_answered(message_history, "diabetic", "hypertension", "no condition", "healthy", "no history")
    state.medications_known = _user_has_answered(message_history, "medication", "medicine", "tablet", "no medication", "not taking")

    for msg in message_history:
        if msg.get("role") == "user":
            trigger = _detect_emergency(msg.get("content", ""))
            if trigger:
                state.stage = ConversationStage.EMERGENCY
                return state

    if state.urgency.lower() in ("emergent", "emergency") or state.risk_level == RiskLevel.CRITICAL:
        state.stage = ConversationStage.EMERGENCY
        return state

    assistant_turns = sum(1 for m in message_history if m.get("role") == "assistant")

    if assistant_turns == 0:
        state.stage = ConversationStage.INITIAL_COLLECT

    elif assistant_turns == 1:
        need_symptom_detail = not (state.duration_known and state.severity_known)
        state.stage = (
            ConversationStage.DEEPEN_SYMPTOMS
            if need_symptom_detail
            else ConversationStage.GATHER_CONTEXT
        )

    elif assistant_turns == 2:
        need_context = not (state.history_known and state.medications_known)
        state.stage = (
            ConversationStage.GATHER_CONTEXT
            if need_context
            else ConversationStage.DELIVER_REPORT
        )

    else:
        state.stage = ConversationStage.DELIVER_REPORT

    return state


# ─────────────────────────────────────────────────────────────
#  SYMPTOM-AWARE QUESTION BUILDER
# ─────────────────────────────────────────────────────────────

SYMPTOM_QUESTIONS: Dict[str, List[str]] = {
    "fever": [
        "How high is your fever (exact temperature if known)?",
        "Do you have chills, sweating, or shivering?",
        "How many days have you had the fever?",
    ],
    "flank pain": [
        "Is the pain on one side or both sides?",
        "Does the pain radiate toward the groin or lower abdomen?",
        "Do you notice burning during urination or blood in urine?",
    ],
    "kidney pain": [
        "Is the pain dull and constant or sharp and cramping?",
        "Any changes in urine colour (dark, cloudy, or pink)?",
        "Any nausea or vomiting alongside the pain?",
    ],
    "headache": [
        "Is the headache on one side or all over?",
        "Rate the pain 1–10 and describe it (throbbing, pressure, stabbing).",
        "Do you have nausea, vomiting, or sensitivity to light/sound?",
    ],
    "cough": [
        "Is the cough dry or productive (producing mucus)?",
        "What colour is the mucus if any?",
        "Do you have fever or difficulty breathing alongside the cough?",
    ],
    "abdominal pain": [
        "Where exactly is the pain (upper/lower, left/right)?",
        "Is the pain constant or does it come and go?",
        "Any nausea, vomiting, diarrhoea, or blood in stool?",
    ],
    "dizziness": [
        "Does the room spin or do you feel faint?",
        "Does it happen when you stand up quickly?",
        "Any ringing in the ears or hearing loss?",
    ],
    "back pain": [
        "Is the pain in the upper or lower back?",
        "Does it shoot down your leg?",
        "Did it start after lifting something heavy or gradually?",
    ],
}

GENERIC_QUESTIONS = [
    "How long have you had these symptoms?",
    "On a scale of 1–10, how severe are they?",
    "Have you had these symptoms before?",
    "Is anything making them better or worse?",
]


def _build_symptom_questions(symptoms: List[str], state: ConversationState) -> List[str]:
    questions: List[str] = []
    matched = False

    for symptom in symptoms:
        for key, qs in SYMPTOM_QUESTIONS.items():
            if key in symptom.lower():
                questions.extend(qs)
                matched = True
                break

    if not matched:
        questions.extend(GENERIC_QUESTIONS)

    if state.duration_known:
        questions = [q for q in questions if not any(
            w in q.lower() for w in ("how long", "how many days", "when did")
        )]
    if state.severity_known:
        questions = [q for q in questions if not any(
            w in q.lower() for w in ("rate", "severe", "scale")
        )]

    return questions[:4]


# ─────────────────────────────────────────────────────────────
#  RESPONSE BUILDERS PER STAGE
# ─────────────────────────────────────────────────────────────

def _build_emergency_response(state: ConversationState) -> str:
    lines = [
        "🚨 **This requires immediate emergency attention.**",
        "",
        "Please do one of the following **right now**:",
        "",
        "- Call **115** (Emergency Rescue Pakistan) or your local emergency number",
        "- Go to the nearest **Emergency Room immediately**",
        "- Ask someone nearby to help you get emergency care",
        "",
        "Do **not** wait or try to manage this at home.",
        "",
        "_This AI is not equipped to handle emergencies. "
        "Your safety is the priority._",
    ]
    return "\n".join(lines)


def _build_initial_response(state: ConversationState) -> str:
    if state.symptoms:
        symptom_list = ", ".join(state.symptoms[:3])
        intro = (
            f"I can see you're experiencing **{symptom_list}**. "
            "I'd like to ask a few targeted questions so I can assess your situation accurately."
        )
    else:
        intro = (
            "I'm here to help. Could you describe your main symptom or "
            "what's bothering you most right now?"
        )

    questions = _build_symptom_questions(state.symptoms, state)
    q_block = "\n".join(f"- {q}" for q in questions)

    return (
        f"{intro}\n\n"
        f"{q_block}\n\n"
        "Please be as specific as possible — this helps me give you a more accurate assessment."
    )


def _build_deepen_response(state: ConversationState) -> str:
    questions = _build_symptom_questions(state.symptoms, state)

    header = "Thank you. I have a few more specific questions to narrow things down:\n"
    q_block = "\n".join(f"- {q}" for q in questions)

    context_prompt = ""
    if not state.duration_known:
        context_prompt += "\n- How long have you been experiencing this?"
    if not state.severity_known:
        context_prompt += "\n- How would you rate the severity (1 = barely noticeable, 10 = unbearable)?"

    return f"{header}\n{q_block}{context_prompt}"


def _build_context_response(state: ConversationState) -> str:
    questions: List[str] = []

    if not state.history_known:
        questions += [
            "Do you have any existing medical conditions (e.g. diabetes, hypertension, asthma)?",
        ]
    if not state.medications_known:
        questions += [
            "Are you currently taking any medications or supplements?",
        ]

    questions += [
        "Have you had similar symptoms in the past? If yes, what was the diagnosis?",
        "Has anything made your symptoms better or worse (e.g. rest, food, movement)?",
    ]

    q_block = "\n".join(f"- {q}" for q in questions[:4])

    return (
        "Thank you for those details. A few final questions to complete the picture:\n\n"
        f"{q_block}\n\n"
        "This context significantly improves the accuracy of the assessment."
    )


async def _build_report_response(state: ConversationState) -> str:
    parts: List[str] = []

    parts += ["## Medical Assessment", ""]

    RISK_BADGES = {
        RiskLevel.LOW:      "🟢 LOW",
        RiskLevel.MODERATE: "🟡 MODERATE",
        RiskLevel.HIGH:     "🔴 HIGH",
        RiskLevel.CRITICAL: "🚨 CRITICAL — Seek care immediately",
    }
    parts += [
        f"**Risk Level:** {RISK_BADGES.get(state.risk_level, 'Unknown')}  "
        f"| **Urgency:** {state.urgency.upper()}",
        "",
    ]

    if state.symptoms:
        parts.append("### Identified Symptoms")
        parts += [f"- {s.capitalize()}" for s in state.symptoms]
        parts.append("")

    if state.conditions:
        parts.append("### Possible Conditions")

        for cond in state.conditions[:3]:
            name       = cond.get("name", "Unknown")
            confidence = float(cond.get("probability", 0))
            conf_bar   = "█" * int(confidence / 10) + "░" * (10 - int(confidence / 10))
            parts.append(f"- **{name}**  `{confidence:.0f}%` {conf_bar}")

        parts.append("")
        parts.append(
            "> ⚠️ These are statistical possibilities, not a confirmed diagnosis. "
            "Only a qualified doctor can diagnose you."
        )
        parts.append("")

    parts += [
        "### Recommended Specialist",
        f"- **{state.specialist}**",
        "",
    ]

    location = state.location or "Islamabad"

    try:
        from app.services.doctor_service import search_doctors

        doctors: List[Dict] = await search_doctors(
            specialty=state.specialist,
            location=location,
        )

        if doctors:
            parts.append(f"### Available {state.specialist}s Near {location}")

            for doc in doctors[:4]:
                name       = doc.get("name", "Unknown")
                hospital   = doc.get("hospital", "Unknown Hospital")
                experience = doc.get("experience", "N/A")
                rating     = doc.get("rating")
                fee        = doc.get("fee")
                available  = doc.get("next_available", "")

                line = f"- **Dr. {name}** — {hospital} · {experience} yrs exp"
                if rating:
                    line += f" · ⭐ {rating}"
                if fee:
                    line += f" · PKR {fee}"
                if available:
                    line += f"\n  📅 Next available: {available}"
                parts.append(line)

            parts.append("")
        else:
            parts += [
                f"No {state.specialist}s found in {location} right now. "
                "Please call a clinic directly or use the search tab.",
                "",
            ]

    except ImportError:
        logger.warning("doctor_service module not available — skipping doctor lookup.")
    except Exception as doctor_err:
        logger.warning("Doctor lookup failed: %s", doctor_err)
        parts += [
            "_Doctor recommendations are temporarily unavailable. "
            "Please use the search tab to find nearby specialists._",
            "",
        ]

    valid_precautions = [
        p for p in state.precautions
        if isinstance(p, str) and len(p.strip()) > 10
    ]
    if valid_precautions:
        parts.append("### What You Can Do Now")
        parts += [f"- {p}" for p in valid_precautions[:5]]
        parts.append("")

    if state.urgency.lower() in ("urgent", "emergent") or state.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        parts += [
            "---",
            "⚠️ **Your symptoms suggest you should see a doctor today — "
            "do not delay if symptoms worsen.**",
            "",
        ]

    parts += [
        "---",
        "_This AI assessment is informational only and does not replace "
        "a consultation with a licensed medical professional._",
    ]

    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────
#  PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────

async def _generate_conversational_response(
    message_history: List[Dict],
    last_user_message: str,
    orchestrator_result: dict,
) -> str:
    """
    Dynamic medical conversation flow.

    Stages (determined from content, not just message count):
      EMERGENCY       → immediate ER instructions, no further questions
      INITIAL_COLLECT → targeted symptom-specific questions
      DEEPEN_SYMPTOMS → follow-up on unanswered specifics
      GATHER_CONTEXT  → medical history & medications
      DELIVER_REPORT  → full assessment + live doctor lookup
    """
    try:
        state = _analyse_conversation(message_history, orchestrator_result)

        logger.info(
            "Conversation stage=%s | symptoms=%s | risk=%s | location=%s",
            state.stage.name,
            state.symptoms,
            state.risk_level.value,
            state.location,
        )

        # ── Stage routing (if/elif replaces match/case for Python 3.9) ──
        if state.stage == ConversationStage.EMERGENCY:
            return _build_emergency_response(state)

        elif state.stage == ConversationStage.INITIAL_COLLECT:
            return _build_initial_response(state)

        elif state.stage == ConversationStage.DEEPEN_SYMPTOMS:
            return _build_deepen_response(state)

        elif state.stage == ConversationStage.GATHER_CONTEXT:
            return _build_context_response(state)

        else:
            # Covers DELIVER_REPORT and any unexpected stage
            return await _build_report_response(state)

    except Exception as exc:
        logger.exception("Conversational response generation failed: %s", exc)
        return (
            "I'm sorry — I encountered an issue generating your assessment. "
            "Please try again, or contact support if the problem persists."
        )