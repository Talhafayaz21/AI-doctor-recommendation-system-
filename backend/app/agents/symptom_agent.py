"""
Symptom Extraction Agent
Extracts rich, structured symptom data from user messages.

Enhancements over v1:
- Fixed OpenAI response parsing (choices[0].message.content)
- Broader symptom vocabulary (100+ symptoms)
- Extracts onset, progression, aggravating/relieving factors
- Detects patient demographics (age group, gender hints)
- Multi-system body-part mapping
- Severity scoring (1-10 scale)
- Structured comorbidity/medication hints
"""

import json
import re
import logging
import httpx
from typing import Dict, Any, List
from app.utils.config import settings
from app.utils.prompts import SYMPTOM_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Vocabulary Banks
# ---------------------------------------------------------------------------

SYMPTOM_VOCABULARY: Dict[str, List[str]] = {
    # General / Constitutional
    "fever": ["fever", "high temperature", "pyrexia", "febrile", "hot to touch", "burning up"],
    "chills": ["chills", "rigors", "shivering", "shaking"],
    "fatigue": ["fatigue", "tiredness", "exhaustion", "lethargy", "weakness", "no energy", "worn out"],
    "weight_loss": ["weight loss", "losing weight", "unexplained weight"],
    "weight_gain": ["weight gain", "gaining weight", "bloated"],
    "night_sweats": ["night sweats", "sweating at night", "drenched at night"],
    "loss_of_appetite": ["loss of appetite", "not hungry", "anorexia", "not eating"],
    "malaise": ["malaise", "general discomfort", "feeling unwell", "under the weather"],

    # Head / Neurological
    "headache": ["headache", "head pain", "head ache", "migraine", "throbbing head", "pressure in head"],
    "dizziness": ["dizziness", "dizzy", "vertigo", "lightheaded", "light headed", "spinning"],
    "confusion": ["confusion", "confused", "disoriented", "not thinking clearly", "brain fog", "forgetfulness"],
    "memory_loss": ["memory loss", "forgetting things", "forgetfulness", "amnesia"],
    "seizure": ["seizure", "convulsion", "fit", "epileptic", "shaking uncontrollably"],
    "fainting": ["fainting", "fainted", "passed out", "syncope", "blackout", "loss of consciousness"],
    "numbness": ["numbness", "numb", "pins and needles", "tingling", "paresthesia"],
    "vision_changes": ["blurry vision", "blurred vision", "double vision", "vision loss", "blind spot", "floaters"],
    "hearing_loss": ["hearing loss", "can't hear", "deafness", "ringing in ears", "tinnitus"],
    "speech_difficulty": ["slurred speech", "difficulty speaking", "can't talk", "aphasia"],

    # Respiratory
    "cough": ["cough", "coughing", "dry cough", "wet cough", "productive cough", "hacking cough"],
    "shortness_of_breath": ["shortness of breath", "breathlessness", "dyspnea", "can't breathe",
                             "difficulty breathing", "breathe", "breathing difficulty", "winded"],
    "wheezing": ["wheezing", "whistling breath", "wheeze"],
    "chest_tightness": ["chest tightness", "tight chest", "pressure on chest"],
    "coughing_blood": ["coughing blood", "blood in sputum", "hemoptysis", "bloody cough"],
    "sore_throat": ["sore throat", "throat pain", "throat ache", "scratchy throat", "strep"],
    "runny_nose": ["runny nose", "nasal discharge", "rhinorrhea", "dripping nose"],
    "nasal_congestion": ["stuffy nose", "blocked nose", "nasal congestion", "can't breathe through nose"],
    "sneezing": ["sneezing", "sneeze"],
    "hoarseness": ["hoarse", "hoarseness", "lost voice", "voice change"],

    # Cardiovascular
    "chest_pain": ["chest pain", "chest ache", "angina", "heart pain", "sternal pain"],
    "palpitations": ["palpitations", "heart racing", "racing heart", "irregular heartbeat",
                     "heart pounding", "fluttering heart", "skipped beats"],
    "edema": ["swollen ankles", "swollen feet", "swollen legs", "edema", "oedema", "swelling in legs"],
    "claudication": ["leg cramps when walking", "pain when walking", "calf pain"],

    # Gastrointestinal
    "nausea": ["nausea", "nauseous", "feeling sick", "queasy", "want to vomit"],
    "vomiting": ["vomiting", "throwing up", "vomit", "emesis", "puking"],
    "diarrhea": ["diarrhea", "diarrhoea", "loose stool", "watery stool", "frequent bowel", "loose motion"],
    "constipation": ["constipation", "constipated", "can't pass stool", "hard stool", "no bowel movement"],
    "abdominal_pain": ["abdominal pain", "stomach pain", "stomach ache", "belly pain", "tummy pain", "gut pain"],
    "bloating": ["bloating", "bloated", "distended abdomen", "gas", "flatulence"],
    "heartburn": ["heartburn", "acid reflux", "indigestion", "gerd", "burning in throat", "acidity"],
    "blood_in_stool": ["blood in stool", "rectal bleeding", "bloody stool", "hematochezia", "melena", "dark stool"],
    "jaundice": ["jaundice", "yellow skin", "yellow eyes", "yellowing"],
    "difficulty_swallowing": ["difficulty swallowing", "dysphagia", "trouble swallowing", "food getting stuck"],

    # Musculoskeletal
    "joint_pain": ["joint pain", "arthralgia", "joint ache", "arthritis", "painful joints"],
    "muscle_pain": ["muscle pain", "myalgia", "body ache", "muscle ache", "sore muscles", "muscle cramps"],
    "back_pain": ["back pain", "backache", "lower back pain", "upper back pain", "spine pain"],
    "neck_pain": ["neck pain", "stiff neck", "neck stiffness", "cervical pain"],
    "swollen_joints": ["swollen joints", "joint swelling", "swollen knee", "swollen fingers"],

    # Urinary / Renal
    "painful_urination": ["painful urination", "burning urination", "dysuria", "pain when peeing", "uti symptoms"],
    "frequent_urination": ["frequent urination", "urinary frequency", "peeing a lot", "pollakiuria"],
    "blood_in_urine": ["blood in urine", "hematuria", "pink urine", "red urine"],
    "urinary_incontinence": ["incontinence", "leaking urine", "can't hold urine"],
    "reduced_urine": ["reduced urine", "not urinating", "oliguria", "no urine", "anuria"],
    "flank_pain": ["flank pain", "kidney pain", "side pain", "loin pain"],

    # Reproductive / Hormonal
    "vaginal_discharge": ["vaginal discharge", "abnormal discharge", "vaginal odour"],
    "menstrual_irregularity": ["irregular periods", "missed period", "heavy periods", "painful periods", "amenorrhea"],
    "pelvic_pain": ["pelvic pain", "lower abdomen pain", "pelvic pressure"],
    "erectile_dysfunction": ["erectile dysfunction", "impotence", "can't get erection"],

    # Skin
    "rash": ["rash", "skin rash", "hives", "urticaria", "red spots", "bumps on skin", "skin eruption"],
    "itching": ["itching", "itchy", "pruritus", "scratching"],
    "skin_discoloration": ["skin discoloration", "pale skin", "skin color change", "cyanosis", "bluish lips"],
    "wounds": ["wound", "cut", "laceration", "sore that won't heal", "ulcer", "bedsore"],
    "hair_loss": ["hair loss", "alopecia", "losing hair", "bald"],

    # Eyes / ENT
    "eye_pain": ["eye pain", "painful eye", "eye ache"],
    "red_eyes": ["red eyes", "pink eye", "conjunctivitis", "bloodshot eyes"],
    "ear_pain": ["ear pain", "earache", "otalgia"],
    "ear_discharge": ["ear discharge", "fluid from ear", "otorrhea"],
    "nasal_bleeding": ["nosebleed", "epistaxis", "bleeding from nose"],

    # Psychiatric / Mental Health
    "anxiety": ["anxiety", "anxious", "worry", "panic attack", "nervousness"],
    "depression": ["depression", "depressed", "hopeless", "sad all the time", "low mood"],
    "insomnia": ["insomnia", "can't sleep", "trouble sleeping", "sleeplessness"],
    "hallucinations": ["hallucinations", "seeing things", "hearing voices"],
}

BODY_PART_MAP: Dict[str, List[str]] = {
    "head": ["head", "skull", "scalp", "temple", "forehead"],
    "eyes": ["eye", "eyes", "vision", "eyelid"],
    "ears": ["ear", "ears", "hearing"],
    "nose": ["nose", "nasal", "nostril"],
    "mouth_throat": ["mouth", "throat", "tongue", "lip", "gum", "tonsil", "pharynx"],
    "neck": ["neck", "cervical", "lymph node", "thyroid"],
    "chest": ["chest", "breast", "lung", "thorax", "sternum", "rib"],
    "heart": ["heart", "cardiac", "palpitation"],
    "abdomen": ["abdomen", "stomach", "belly", "gut", "navel", "umbilical"],
    "pelvis": ["pelvis", "pelvic", "groin", "hip", "inguinal"],
    "back": ["back", "spine", "lumbar", "sacral", "dorsal"],
    "upper_limbs": ["arm", "elbow", "wrist", "hand", "finger", "shoulder", "forearm"],
    "lower_limbs": ["leg", "knee", "ankle", "foot", "toe", "thigh", "calf", "shin"],
    "skin": ["skin", "rash", "wound", "ulcer", "sore"],
    "urinary": ["bladder", "urine", "urinary", "kidney", "renal", "flank"],
    "genitals": ["genital", "vagina", "uterus", "penis", "scrotum", "testicle", "ovary"],
    "muscles_joints": ["muscle", "joint", "tendon", "ligament", "bone"],
    "lymphatics": ["lymph", "lymph node", "gland"],
}

SEVERITY_SCALE = {
    "mild": {"score": 3, "keywords": ["mild", "slight", "minor", "little", "a bit", "slightly", "occasional"]},
    "moderate": {"score": 5, "keywords": ["moderate", "somewhat", "moderate", "regular", "manageable"]},
    "severe": {"score": 8, "keywords": ["severe", "terrible", "awful", "extreme", "intense", "horrible", "very bad", "excruciating", "unbearable", "worst ever"]},
    "critical": {"score": 10, "keywords": ["can't move", "incapacitated", "life-threatening", "emergency", "critical", "collapsing"]},
}

DURATION_PATTERNS = [
    (r"\b(\d+)\s*hour[s]?\b", "hours"),
    (r"\b(\d+)\s*day[s]?\b", "days"),
    (r"\b(\d+)\s*week[s]?\b", "weeks"),
    (r"\b(\d+)\s*month[s]?\b", "months"),
    (r"\b(\d+)\s*year[s]?\b", "years"),
    (r"\bsince\s+(yesterday|last\s+\w+|this\s+morning)\b", "recent"),
    (r"\bfor\s+a\s+(while|long\s+time)\b", "chronic"),
    (r"\b(today|just\s+started|sudden|acute)\b", "acute - today"),
    (r"\b(chronic|long.standing|ongoing|persistent)\b", "chronic"),
]

AGGRAVATING_KEYWORDS = [
    "worse when", "worsens with", "aggravated by", "triggered by",
    "gets worse", "more pain when", "exacerbated by", "increases with",
]

RELIEVING_KEYWORDS = [
    "better when", "relieved by", "eases with", "improves with",
    "helps when", "gets better", "reduces when",
]

AGE_PATTERNS = [
    (r"\b(\d{1,2})\s*year[s]?\s*old\b", "exact"),
    (r"\bage\s*(\d{1,2})\b", "exact"),
    (r"\bbaby\b|\binfant\b|\bnewborn\b", "0-2"),
    (r"\btoddler\b|\bchild\b|\bkid\b", "3-12"),
    (r"\bteen\b|\bteenager\b|\badolescent\b", "13-18"),
    (r"\byoung adult\b", "19-35"),
    (r"\badult\b", "36-60"),
    (r"\belderly\b|\bsenior\b|\bolder\b|\bold\s+man\b|\bold\s+woman\b", "60+"),
]

GENDER_KEYWORDS = {
    "male": ["male", "man", "boy", "he", "his", "him", "husband", "father", "son", "brother", "uncle"],
    "female": ["female", "woman", "girl", "she", "her", "wife", "mother", "daughter", "sister", "aunt"],
}


class SymptomAgent:
    """Agent responsible for extracting rich structured symptom data from user input."""

    def __init__(self):
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.model = settings.OPENAI_MODEL
        self.api_key = settings.OPENAI_API_KEY

        # Check if API key is properly set (not placeholder)
        if self.api_key and ("your-" in self.api_key.lower() or "here" in self.api_key.lower()):
            logger.warning("OpenAI API key appears to be placeholder - using fallback mode")
            self.api_key = None

    async def extract(self, user_message: str) -> dict:
        """
        Extract comprehensive symptom profile from user message.

        Returns dict with keys:
            symptoms, body_parts, duration, onset, severity, severity_score,
            aggravating_factors, relieving_factors, patient_age, patient_gender,
            associated_symptoms, red_flags
        """

        # Check if API key is available
        if not self.api_key:
            logger.info("OpenAI API key not available - using fallback extraction")
            return self._fallback_extraction(user_message)

        system_prompt = self._build_system_prompt()

        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (
                    f"Extract a complete medical symptom profile from this message. "
                    f"Return ONLY valid JSON:\n\n{user_message}"
                )},
            ],
            "temperature": 0.0,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            # ✅ Fixed: correct OpenAI response path
            raw_text = data["choices"][0]["message"]["content"]
            return self._parse_json_response(raw_text)

        except Exception as e:
            logger.warning(f"OpenAI API failed for symptom extraction: {e}. Using enhanced fallback.")
            return self._fallback_extraction(user_message)

    # ------------------------------------------------------------------ #
    #  System Prompt                                                       #
    # ------------------------------------------------------------------ #

    def _build_system_prompt(self) -> str:
        return """You are a medical symptom extraction AI. Extract ALL clinically relevant information 
from the user's message and return ONLY a JSON object with these exact keys:

{
  "symptoms": ["list of symptoms as concise medical terms"],
  "body_parts": ["list of affected body parts/systems"],
  "duration": "string describing duration (e.g., '3 days', '2 weeks', 'since this morning')",
  "onset": "acute | gradual | sudden | unknown",
  "severity": "mild | moderate | severe | critical",
  "severity_score": 1-10 integer,
  "aggravating_factors": ["list of things that make it worse"],
  "relieving_factors": ["list of things that make it better"],
  "patient_age": "age string or null",
  "patient_gender": "male | female | unknown",
  "associated_symptoms": ["secondary symptoms mentioned"],
  "red_flags": ["any alarming symptoms that need urgent attention"],
  "possible_allergies": ["any allergies mentioned"],
  "current_medications": ["any medications mentioned"],
  "medical_history": ["any past conditions mentioned"]
}

Rules:
- Use standard medical terminology where appropriate
- red_flags should include: chest pain, difficulty breathing, loss of consciousness, severe bleeding, stroke symptoms, etc.
- Be thorough — include ALL symptoms mentioned, even if seemingly minor
- severity_score: 1-3=mild, 4-6=moderate, 7-8=severe, 9-10=critical"""

    # ------------------------------------------------------------------ #
    #  Enhanced Fallback                                                   #
    # ------------------------------------------------------------------ #

    def _fallback_extraction(self, user_message: str) -> dict:
        """Comprehensive rule-based extraction when API is unavailable."""
        text = user_message.lower()

        symptoms = self._extract_symptoms(text)
        body_parts = self._extract_body_parts(text)
        severity, severity_score = self._extract_severity(text)
        duration = self._extract_duration(user_message)
        onset = self._extract_onset(text)
        aggravating = self._extract_context_phrases(text, AGGRAVATING_KEYWORDS)
        relieving = self._extract_context_phrases(text, RELIEVING_KEYWORDS)
        patient_age = self._extract_age(user_message)
        patient_gender = self._extract_gender(text)
        red_flags = self._extract_red_flags(symptoms, text)

        return {
            "symptoms": symptoms if symptoms else ["general discomfort"],
            "body_parts": body_parts,
            "duration": duration,
            "onset": onset,
            "severity": severity,
            "severity_score": severity_score,
            "aggravating_factors": aggravating,
            "relieving_factors": relieving,
            "patient_age": patient_age,
            "patient_gender": patient_gender,
            "associated_symptoms": [],
            "red_flags": red_flags,
            "possible_allergies": [],
            "current_medications": self._extract_medications(text),
            "medical_history": self._extract_history(text),
        }

    def _extract_symptoms(self, text: str) -> List[str]:
        found = []
        for canonical, aliases in SYMPTOM_VOCABULARY.items():
            if any(alias in text for alias in aliases):
                found.append(canonical.replace("_", " "))
        return found

    def _extract_body_parts(self, text: str) -> List[str]:
        found = []
        for part, keywords in BODY_PART_MAP.items():
            if any(kw in text for kw in keywords):
                found.append(part.replace("_", " "))
        return found

    def _extract_severity(self, text: str):
        for level in ["critical", "severe", "moderate", "mild"]:
            info = SEVERITY_SCALE[level]
            if any(kw in text for kw in info["keywords"]):
                return level, info["score"]
        return "moderate", 5

    def _extract_duration(self, text: str) -> str:
        for pattern, unit in DURATION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if match.lastindex and match.group(1).isdigit():
                    return f"{match.group(1)} {unit}"
                return unit
        return "unknown"

    def _extract_onset(self, text: str) -> str:
        if any(w in text for w in ["sudden", "suddenly", "all of a sudden", "acute", "just now", "started abruptly"]):
            return "sudden"
        if any(w in text for w in ["gradually", "slowly", "over time", "progressively"]):
            return "gradual"
        if any(w in text for w in ["today", "this morning", "few hours"]):
            return "acute"
        return "unknown"

    def _extract_context_phrases(self, text: str, trigger_keywords: List[str]) -> List[str]:
        results = []
        for trigger in trigger_keywords:
            idx = text.find(trigger)
            if idx != -1:
                snippet = text[idx + len(trigger):idx + len(trigger) + 60].strip()
                snippet = re.split(r"[,.\n]", snippet)[0].strip()
                if snippet:
                    results.append(snippet)
        return results[:3]

    def _extract_age(self, text: str) -> str:
        for pattern, kind in AGE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if kind == "exact" and match.lastindex:
                    return f"{match.group(1)} years"
                return kind
        return None

    def _extract_gender(self, text: str) -> str:
        for gender, keywords in GENDER_KEYWORDS.items():
            if any(kw in text.split() for kw in keywords):
                return gender
        return "unknown"

    def _extract_red_flags(self, symptoms: List[str], text: str) -> List[str]:
        flags = []
        red_flag_symptoms = [
            "chest pain", "shortness of breath", "coughing blood", "blood in stool",
            "blood in urine", "seizure", "fainting", "confusion", "speech difficulty",
            "vision changes", "numbness", "severe headache",
        ]
        flags.extend([s for s in symptoms if s in red_flag_symptoms])

        critical_phrases = [
            "can't breathe", "cannot breathe", "losing consciousness",
            "severe chest pain", "vomiting blood", "stroke", "paralysis",
        ]
        for phrase in critical_phrases:
            if phrase in text and phrase not in flags:
                flags.append(phrase)
        return flags

    def _extract_medications(self, text: str) -> List[str]:
        med_keywords = [
            "taking", "prescribed", "medication", "medicine", "drug",
            "paracetamol", "ibuprofen", "aspirin", "antibiotic", "steroid",
            "insulin", "metformin", "lisinopril", "amlodipine",
        ]
        if any(kw in text for kw in med_keywords):
            return ["medications mentioned — review with physician"]
        return []

    def _extract_history(self, text: str) -> List[str]:
        history_keywords = {
            "diabetes": ["diabetic", "diabetes", "sugar patient", "high blood sugar"],
            "hypertension": ["hypertension", "high blood pressure", "bp problem"],
            "heart disease": ["heart disease", "heart attack", "cardiac", "heart condition"],
            "asthma": ["asthma", "asthmatic"],
            "thyroid": ["thyroid", "hypothyroid", "hyperthyroid"],
            "kidney disease": ["kidney disease", "renal failure", "ckd"],
            "liver disease": ["liver disease", "hepatitis", "cirrhosis"],
            "cancer": ["cancer", "tumor", "malignancy", "oncology"],
        }
        found = []
        for condition, keywords in history_keywords.items():
            if any(kw in text for kw in keywords):
                found.append(condition)
        return found

    # ------------------------------------------------------------------ #
    #  JSON Parser                                                         #
    # ------------------------------------------------------------------ #

    def _parse_json_response(self, raw_text: str) -> dict:
        clean = re.sub(r"```(?:json)?|```", "", raw_text).strip()
        try:
            result = json.loads(clean)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM JSON response for symptoms.")
            result = {}

        result.setdefault("symptoms", [])
        result.setdefault("body_parts", [])
        result.setdefault("duration", "unknown")
        result.setdefault("onset", "unknown")
        result.setdefault("severity", "unknown")
        result.setdefault("severity_score", 5)
        result.setdefault("aggravating_factors", [])
        result.setdefault("relieving_factors", [])
        result.setdefault("patient_age", None)
        result.setdefault("patient_gender", "unknown")
        result.setdefault("associated_symptoms", [])
        result.setdefault("red_flags", [])
        result.setdefault("possible_allergies", [])
        result.setdefault("current_medications", [])
        result.setdefault("medical_history", [])
        return result


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_agent_instance = None


async def analyze(user_message: str) -> dict:
    """Module-level wrapper for symptom extraction."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = SymptomAgent()
    return await _agent_instance.extract(user_message)