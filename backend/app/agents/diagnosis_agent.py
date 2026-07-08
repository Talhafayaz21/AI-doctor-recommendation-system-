"""
Diagnosis / Medical Reasoning Agent
Analyzes extracted symptoms and suggests possible conditions.

Enhancements over v1:
- Fixed OpenAI response parsing bug (choices[0].message.content)
- ICD-10 code hints for each condition
- Confidence scoring (0.0–1.0)
- Differential diagnosis with reasoning
- 15+ symptom pattern categories (vs 3 before)
- Urgency tier: routine | urgent | emergent
- Risk factors considered (age, gender, comorbidities)
- Follow-up questions generated
"""

import json
import re
import logging
import httpx
from typing import Dict, Any, List, Tuple
from app.utils.config import settings
from app.utils.prompts import MEDICAL_REASONING_PROMPT

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Condition Knowledge Base
# ---------------------------------------------------------------------------

CONDITION_DB: Dict[str, Dict] = {
    # Respiratory
    "Common Cold": {
        "icd10": "J00",
        "specialist": "General Practitioner",
        "keywords": ["runny nose", "sore throat", "sneezing", "nasal congestion", "mild fever", "cough"],
        "urgency": "routine",
        "base_probability": 0.7,
    },
    "Influenza": {
        "icd10": "J09-J11",
        "specialist": "General Practitioner",
        "keywords": ["fever", "chills", "body ache", "fatigue", "cough", "headache"],
        "urgency": "routine",
        "base_probability": 0.6,
    },
    "Pneumonia": {
        "icd10": "J18",
        "specialist": "Pulmonologist",
        "keywords": ["fever", "cough", "shortness of breath", "chest pain", "fatigue"],
        "urgency": "urgent",
        "base_probability": 0.3,
    },
    "Asthma Exacerbation": {
        "icd10": "J45",
        "specialist": "Pulmonologist",
        "keywords": ["wheezing", "shortness of breath", "chest tightness", "cough"],
        "urgency": "urgent",
        "base_probability": 0.4,
    },
    "COVID-19": {
        "icd10": "U07.1",
        "specialist": "General Practitioner / Infectious Disease",
        "keywords": ["fever", "cough", "fatigue", "loss of appetite", "shortness of breath", "body ache"],
        "urgency": "urgent",
        "base_probability": 0.5,
    },
    "Tuberculosis": {
        "icd10": "A15",
        "specialist": "Pulmonologist / Infectious Disease",
        "keywords": ["cough", "night sweats", "weight loss", "fever", "fatigue", "coughing blood"],
        "urgency": "urgent",
        "base_probability": 0.2,
    },
    "Pulmonary Embolism": {
        "icd10": "I26",
        "specialist": "Emergency Medicine",
        "keywords": ["shortness of breath", "chest pain", "coughing blood", "leg swelling"],
        "urgency": "emergent",
        "base_probability": 0.15,
    },

    # Cardiovascular
    "Hypertension": {
        "icd10": "I10",
        "specialist": "Cardiologist",
        "keywords": ["headache", "dizziness", "vision changes", "chest pain", "palpitations"],
        "urgency": "routine",
        "base_probability": 0.5,
    },
    "Acute Myocardial Infarction (Heart Attack)": {
        "icd10": "I21",
        "specialist": "Cardiologist / Emergency Medicine",
        "keywords": ["chest pain", "shortness of breath", "nausea", "sweating", "arm pain", "jaw pain"],
        "urgency": "emergent",
        "base_probability": 0.2,
    },
    "Heart Failure": {
        "icd10": "I50",
        "specialist": "Cardiologist",
        "keywords": ["shortness of breath", "edema", "fatigue", "cough", "weight gain", "palpitations"],
        "urgency": "urgent",
        "base_probability": 0.25,
    },
    "Atrial Fibrillation": {
        "icd10": "I48",
        "specialist": "Cardiologist",
        "keywords": ["palpitations", "fatigue", "dizziness", "shortness of breath", "chest pain"],
        "urgency": "urgent",
        "base_probability": 0.3,
    },
    "Angina Pectoris": {
        "icd10": "I20",
        "specialist": "Cardiologist",
        "keywords": ["chest pain", "shortness of breath", "dizziness", "fatigue"],
        "urgency": "urgent",
        "base_probability": 0.35,
    },

    # Neurological
    "Migraine": {
        "icd10": "G43",
        "specialist": "Neurologist",
        "keywords": ["headache", "nausea", "vomiting", "vision changes", "dizziness", "light sensitivity"],
        "urgency": "routine",
        "base_probability": 0.6,
    },
    "Tension Headache": {
        "icd10": "G44.2",
        "specialist": "General Practitioner",
        "keywords": ["headache", "neck pain", "fatigue", "stress"],
        "urgency": "routine",
        "base_probability": 0.7,
    },
    "Stroke / TIA": {
        "icd10": "I63 / G45",
        "specialist": "Neurologist / Emergency Medicine",
        "keywords": ["speech difficulty", "numbness", "vision changes", "confusion", "severe headache", "fainting"],
        "urgency": "emergent",
        "base_probability": 0.15,
    },
    "Epilepsy / Seizure Disorder": {
        "icd10": "G40",
        "specialist": "Neurologist",
        "keywords": ["seizure", "fainting", "confusion", "memory loss", "muscle pain"],
        "urgency": "urgent",
        "base_probability": 0.2,
    },
    "Meningitis": {
        "icd10": "G03",
        "specialist": "Neurologist / Infectious Disease",
        "keywords": ["severe headache", "fever", "neck pain", "confusion", "nausea", "vomiting", "rash"],
        "urgency": "emergent",
        "base_probability": 0.1,
    },
    "Parkinson's Disease": {
        "icd10": "G20",
        "specialist": "Neurologist",
        "keywords": ["muscle pain", "confusion", "memory loss", "weakness", "fatigue"],
        "urgency": "routine",
        "base_probability": 0.1,
    },

    # Gastrointestinal
    "Gastroenteritis": {
        "icd10": "A09",
        "specialist": "General Practitioner",
        "keywords": ["nausea", "vomiting", "diarrhea", "abdominal pain", "fever", "fatigue"],
        "urgency": "routine",
        "base_probability": 0.65,
    },
    "Food Poisoning": {
        "icd10": "A05",
        "specialist": "General Practitioner",
        "keywords": ["nausea", "vomiting", "diarrhea", "abdominal pain", "fever"],
        "urgency": "routine",
        "base_probability": 0.5,
    },
    "Peptic Ulcer Disease": {
        "icd10": "K27",
        "specialist": "Gastroenterologist",
        "keywords": ["abdominal pain", "heartburn", "nausea", "vomiting", "blood in stool", "loss of appetite"],
        "urgency": "routine",
        "base_probability": 0.3,
    },
    "Appendicitis": {
        "icd10": "K37",
        "specialist": "General Surgeon",
        "keywords": ["abdominal pain", "fever", "nausea", "vomiting", "loss of appetite"],
        "urgency": "emergent",
        "base_probability": 0.2,
    },
    "Irritable Bowel Syndrome": {
        "icd10": "K58",
        "specialist": "Gastroenterologist",
        "keywords": ["abdominal pain", "bloating", "diarrhea", "constipation", "nausea"],
        "urgency": "routine",
        "base_probability": 0.4,
    },
    "Hepatitis": {
        "icd10": "B15-B19",
        "specialist": "Gastroenterologist / Hepatologist",
        "keywords": ["jaundice", "fatigue", "abdominal pain", "nausea", "vomiting", "loss of appetite"],
        "urgency": "urgent",
        "base_probability": 0.2,
    },
    "Cholecystitis": {
        "icd10": "K81",
        "specialist": "General Surgeon",
        "keywords": ["abdominal pain", "nausea", "vomiting", "fever", "jaundice"],
        "urgency": "urgent",
        "base_probability": 0.2,
    },
    "Crohn's Disease": {
        "icd10": "K50",
        "specialist": "Gastroenterologist",
        "keywords": ["diarrhea", "abdominal pain", "blood in stool", "weight loss", "fatigue", "fever"],
        "urgency": "routine",
        "base_probability": 0.15,
    },
    "GERD": {
        "icd10": "K21",
        "specialist": "Gastroenterologist",
        "keywords": ["heartburn", "difficulty swallowing", "chest pain", "nausea", "hoarseness"],
        "urgency": "routine",
        "base_probability": 0.5,
    },

    # Musculoskeletal
    "Rheumatoid Arthritis": {
        "icd10": "M06",
        "specialist": "Rheumatologist",
        "keywords": ["joint pain", "swollen joints", "fatigue", "fever", "morning stiffness"],
        "urgency": "routine",
        "base_probability": 0.2,
    },
    "Osteoarthritis": {
        "icd10": "M15-M19",
        "specialist": "Orthopedic Surgeon / Rheumatologist",
        "keywords": ["joint pain", "stiffness", "swollen joints", "back pain"],
        "urgency": "routine",
        "base_probability": 0.4,
    },
    "Gout": {
        "icd10": "M10",
        "specialist": "Rheumatologist",
        "keywords": ["joint pain", "swollen joints", "severe pain", "redness"],
        "urgency": "routine",
        "base_probability": 0.25,
    },
    "Fibromyalgia": {
        "icd10": "M79.7",
        "specialist": "Rheumatologist",
        "keywords": ["muscle pain", "fatigue", "insomnia", "headache", "depression", "anxiety"],
        "urgency": "routine",
        "base_probability": 0.2,
    },
    "Lower Back Pain": {
        "icd10": "M54.5",
        "specialist": "Orthopedic Surgeon / Physiotherapist",
        "keywords": ["back pain", "muscle pain", "numbness", "weakness"],
        "urgency": "routine",
        "base_probability": 0.6,
    },

    # Endocrine / Metabolic
    "Diabetes Mellitus Type 2": {
        "icd10": "E11",
        "specialist": "Endocrinologist",
        "keywords": ["frequent urination", "fatigue", "weight loss", "vision changes", "wounds", "numbness"],
        "urgency": "routine",
        "base_probability": 0.3,
    },
    "Hypothyroidism": {
        "icd10": "E03",
        "specialist": "Endocrinologist",
        "keywords": ["fatigue", "weight gain", "hair loss", "depression", "constipation", "cold intolerance"],
        "urgency": "routine",
        "base_probability": 0.25,
    },
    "Hyperthyroidism": {
        "icd10": "E05",
        "specialist": "Endocrinologist",
        "keywords": ["weight loss", "palpitations", "anxiety", "sweating", "diarrhea", "fatigue", "hair loss"],
        "urgency": "routine",
        "base_probability": 0.2,
    },
    "Anemia": {
        "icd10": "D64",
        "specialist": "Hematologist / General Practitioner",
        "keywords": ["fatigue", "weakness", "dizziness", "shortness of breath", "palpitations", "skin discoloration"],
        "urgency": "routine",
        "base_probability": 0.4,
    },

    # Urinary / Renal
    "Urinary Tract Infection (UTI)": {
        "icd10": "N39.0",
        "specialist": "General Practitioner / Urologist",
        "keywords": ["painful urination", "frequent urination", "fever", "flank pain", "blood in urine"],
        "urgency": "routine",
        "base_probability": 0.6,
    },
    "Kidney Stones": {
        "icd10": "N20",
        "specialist": "Urologist",
        "keywords": ["flank pain", "blood in urine", "painful urination", "nausea", "vomiting"],
        "urgency": "urgent",
        "base_probability": 0.3,
    },
    "Chronic Kidney Disease": {
        "icd10": "N18",
        "specialist": "Nephrologist",
        "keywords": ["fatigue", "reduced urine", "edema", "nausea", "weakness", "itching"],
        "urgency": "urgent",
        "base_probability": 0.15,
    },

    # Mental Health
    "Major Depressive Disorder": {
        "icd10": "F32",
        "specialist": "Psychiatrist / Psychologist",
        "keywords": ["depression", "fatigue", "insomnia", "loss of appetite", "weight loss", "anxiety"],
        "urgency": "routine",
        "base_probability": 0.35,
    },
    "Generalized Anxiety Disorder": {
        "icd10": "F41.1",
        "specialist": "Psychiatrist / Psychologist",
        "keywords": ["anxiety", "palpitations", "insomnia", "fatigue", "headache", "dizziness"],
        "urgency": "routine",
        "base_probability": 0.4,
    },
    "Panic Disorder": {
        "icd10": "F41.0",
        "specialist": "Psychiatrist",
        "keywords": ["anxiety", "palpitations", "shortness of breath", "chest pain", "dizziness", "fear"],
        "urgency": "routine",
        "base_probability": 0.3,
    },

    # Dermatological
    "Eczema / Atopic Dermatitis": {
        "icd10": "L20",
        "specialist": "Dermatologist",
        "keywords": ["rash", "itching", "skin discoloration"],
        "urgency": "routine",
        "base_probability": 0.35,
    },
    "Psoriasis": {
        "icd10": "L40",
        "specialist": "Dermatologist",
        "keywords": ["rash", "itching", "skin discoloration", "joint pain"],
        "urgency": "routine",
        "base_probability": 0.2,
    },
    "Cellulitis": {
        "icd10": "L03",
        "specialist": "Dermatologist / General Practitioner",
        "keywords": ["rash", "fever", "wounds", "swollen joints", "redness"],
        "urgency": "urgent",
        "base_probability": 0.2,
    },

    # Infections
    "Typhoid Fever": {
        "icd10": "A01.0",
        "specialist": "Infectious Disease / General Practitioner",
        "keywords": ["fever", "abdominal pain", "diarrhea", "headache", "fatigue", "rash"],
        "urgency": "urgent",
        "base_probability": 0.3,
    },
    "Dengue Fever": {
        "icd10": "A90",
        "specialist": "Infectious Disease / General Practitioner",
        "keywords": ["fever", "headache", "body ache", "joint pain", "rash", "fatigue", "vomiting"],
        "urgency": "urgent",
        "base_probability": 0.35,
    },
    "Malaria": {
        "icd10": "B50-B54",
        "specialist": "Infectious Disease",
        "keywords": ["fever", "chills", "headache", "fatigue", "nausea", "vomiting", "sweating"],
        "urgency": "urgent",
        "base_probability": 0.25,
    },
}

# Urgency-to-risk mapping
URGENCY_RISK_MAP = {
    "emergent": "high",
    "urgent": "medium",
    "routine": "low",
}


class DiagnosisAgent:
    """Agent responsible for rich medical reasoning from structured symptom data."""

    def __init__(self):
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.model   = settings.OPENAI_MODEL
        self.api_key = settings.OPENAI_API_KEY

        # Check if API key is properly set (not placeholder)
        if self.api_key and ("your-" in self.api_key.lower() or "here" in self.api_key.lower()):
            logger.warning("OpenAI API key appears to be placeholder - using fallback mode")
            self.api_key = None

    async def analyze(self, symptom_data: dict) -> dict:
        """
        Analyze symptom data and return differential diagnoses.

        Returns dict with:
            conditions (list), risk_level, urgency, follow_up_questions,
            red_flags, confidence, reasoning_summary
        """

        # Check if API key is available
        if not self.api_key:
            logger.info("OpenAI API key not available - using fallback diagnosis")
            return self._fallback_diagnosis(symptom_data)

        symptom_summary = self._build_symptom_summary(symptom_data)
        system_prompt = self._build_system_prompt()

        payload = {
            "model": self.model,
            "max_tokens": 1500,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Perform a differential diagnosis for the following structured "
                        f"symptom profile. Return ONLY valid JSON:\n\n{symptom_summary}"
                    ),
                },
            ],
            "temperature": 0.2,
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

            # ✅ Fixed: correct OpenAI response path
            raw_text = data["choices"][0]["message"]["content"]
            return self._parse_json_response(raw_text)

        except Exception as e:
            logger.warning(f"OpenAI API failed for diagnosis: {e}. Using enhanced fallback.")
            return self._fallback_diagnosis(symptom_data)

    # ------------------------------------------------------------------ #
    #  System Prompt                                                       #
    # ------------------------------------------------------------------ #

    def _build_system_prompt(self) -> str:
        return """You are an expert medical AI performing differential diagnosis. Analyze the symptom profile 
and return ONLY a JSON object with this exact structure:

{
  "conditions": [
    {
      "name": "Condition Name",
      "icd10": "ICD-10 code",
      "probability": "high | moderate | low",
      "confidence": 0.0-1.0 float,
      "reasoning": "brief clinical reasoning for this diagnosis",
      "specialist": "recommended specialist type",
      "urgency": "emergent | urgent | routine"
    }
  ],
  "risk_level": "high | medium | low",
  "urgency": "emergent | urgent | routine",
  "reasoning_summary": "brief paragraph summarizing the clinical picture",
  "red_flags": ["list of alarming features detected"],
  "follow_up_questions": ["2-4 clarifying questions a doctor would ask"],
  "recommended_tests": ["relevant diagnostic tests to consider"],
  "differential_notes": "any important differential diagnosis considerations"
}

Rules:
- List up to 5 conditions, ordered by likelihood (most likely first)
- Always be medically conservative — flag emergent conditions even at low probability
- If red_flags are present, urgency should be at least 'urgent'
- follow_up_questions should help narrow the differential
- recommended_tests should be clinically appropriate (e.g., CBC, CXR, ECG, urinalysis)
- Do NOT prescribe medications or give definitive diagnoses
- Add disclaimer context in reasoning_summary"""

    # ------------------------------------------------------------------ #
    #  Symptom Summary Builder                                            #
    # ------------------------------------------------------------------ #

    def _build_symptom_summary(self, symptom_data: dict) -> str:
        symptoms = ", ".join(symptom_data.get("symptoms", [])) or "none reported"
        associated = ", ".join(symptom_data.get("associated_symptoms", [])) or "none"
        body_parts = ", ".join(symptom_data.get("body_parts", [])) or "unspecified"
        duration = symptom_data.get("duration", "unknown")
        onset = symptom_data.get("onset", "unknown")
        severity = symptom_data.get("severity", "unknown")
        severity_score = symptom_data.get("severity_score", "N/A")
        red_flags = ", ".join(symptom_data.get("red_flags", [])) or "none"
        aggravating = ", ".join(symptom_data.get("aggravating_factors", [])) or "none"
        relieving = ", ".join(symptom_data.get("relieving_factors", [])) or "none"
        age = symptom_data.get("patient_age") or "unknown"
        gender = symptom_data.get("patient_gender", "unknown")
        history = ", ".join(symptom_data.get("medical_history", [])) or "none"
        medications = ", ".join(symptom_data.get("current_medications", [])) or "none"

        return (
            f"Primary Symptoms: {symptoms}\n"
            f"Associated Symptoms: {associated}\n"
            f"Body Parts Affected: {body_parts}\n"
            f"Duration: {duration}\n"
            f"Onset: {onset}\n"
            f"Severity: {severity} (score: {severity_score}/10)\n"
            f"Aggravating Factors: {aggravating}\n"
            f"Relieving Factors: {relieving}\n"
            f"Red Flags: {red_flags}\n"
            f"Patient Age: {age}\n"
            f"Patient Gender: {gender}\n"
            f"Medical History: {history}\n"
            f"Current Medications: {medications}"
        )

    # ------------------------------------------------------------------ #
    #  Enhanced Fallback Diagnosis                                         #
    # ------------------------------------------------------------------ #

    def _fallback_diagnosis(self, symptom_data: dict) -> dict:
        symptoms = symptom_data.get("symptoms", [])
        red_flags = symptom_data.get("red_flags", [])
        severity = symptom_data.get("severity", "moderate")
        severity_score = symptom_data.get("severity_score", 5)
        medical_history = symptom_data.get("medical_history", [])

        symptom_set = set(symptoms)

        # Score each condition against symptom overlap
        scored: List[Tuple[str, float, dict]] = []
        for condition_name, info in CONDITION_DB.items():
            keywords = set(info["keywords"])
            overlap = len(symptom_set & keywords)
            if overlap == 0:
                continue
            score = (overlap / len(keywords)) * info["base_probability"]

            # Boost score if condition appears in medical history
            for hist in medical_history:
                if hist.lower() in condition_name.lower():
                    score *= 1.5

            scored.append((condition_name, score, info))

        # Sort by score descending, take top 5
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:5]

        conditions = []
        urgency_levels = []
        for name, score, info in top:
            if score >= 0.4:
                probability = "high"
                confidence = min(score, 0.9)
            elif score >= 0.2:
                probability = "moderate"
                confidence = min(score, 0.6)
            else:
                probability = "low"
                confidence = min(score, 0.3)

            urgency_levels.append(info["urgency"])
            conditions.append({
                "name": name,
                "icd10": info["icd10"],
                "probability": probability,
                "confidence": round(confidence, 2),
                "reasoning": f"Symptom overlap with {name} pattern detected.",
                "specialist": info["specialist"],
                "urgency": info["urgency"],
            })

        # If no conditions matched, add default
        if not conditions:
            conditions = [
                {
                    "name": "Viral Syndrome",
                    "icd10": "B34.9",
                    "probability": "moderate",
                    "confidence": 0.4,
                    "reasoning": "Non-specific viral illness consistent with general symptoms.",
                    "specialist": "General Practitioner",
                    "urgency": "routine",
                },
                {
                    "name": "General Infection",
                    "icd10": "A49.9",
                    "probability": "low",
                    "confidence": 0.2,
                    "reasoning": "Infection possible based on constitutional symptoms.",
                    "specialist": "General Practitioner",
                    "urgency": "routine",
                },
            ]
            urgency_levels = ["routine"]

        # Determine overall urgency and risk
        if red_flags or severity_score >= 8 or "emergent" in urgency_levels:
            overall_urgency = "emergent"
        elif severity_score >= 6 or "urgent" in urgency_levels:
            overall_urgency = "urgent"
        else:
            overall_urgency = "routine"

        risk_level = URGENCY_RISK_MAP.get(overall_urgency, "medium")

        follow_up_questions = [
            "How long have you had these symptoms?",
            "Do you have any known medical conditions or allergies?",
            "Are you currently taking any medications?",
            "Have these symptoms been getting better, worse, or staying the same?",
        ]

        recommended_tests = self._suggest_tests(symptoms, conditions)

        return {
            "conditions": conditions,
            "risk_level": risk_level,
            "urgency": overall_urgency,
            "reasoning_summary": (
                f"Based on reported symptoms, {len(conditions)} possible condition(s) identified. "
                f"Overall urgency is {overall_urgency}. This is a preliminary assessment — "
                f"please consult a qualified healthcare professional for proper diagnosis."
            ),
            "red_flags": red_flags,
            "follow_up_questions": follow_up_questions,
            "recommended_tests": recommended_tests,
            "differential_notes": "Rule-based fallback used. LLM validation recommended.",
        }

    def _suggest_tests(self, symptoms: List[str], conditions: List[dict]) -> List[str]:
        tests = set()
        symptom_test_map = {
            "fever": ["Complete Blood Count (CBC)", "Blood Culture", "CRP / ESR"],
            "chest pain": ["ECG (12-lead)", "Cardiac Enzymes (Troponin)", "Chest X-Ray"],
            "shortness of breath": ["Chest X-Ray", "Pulse Oximetry", "Spirometry"],
            "cough": ["Chest X-Ray", "Sputum Culture", "CBC"],
            "headache": ["Blood Pressure Measurement", "CT Head (if severe)"],
            "nausea": ["Liver Function Tests", "Abdominal Ultrasound"],
            "abdominal pain": ["Abdominal Ultrasound", "LFTs", "Amylase/Lipase", "Urinalysis"],
            "joint pain": ["Uric Acid", "Rheumatoid Factor", "ANA", "ESR"],
            "fatigue": ["CBC", "Thyroid Function Tests (TFT)", "Blood Glucose", "Ferritin"],
            "frequent urination": ["Urinalysis", "Urine Culture", "Blood Glucose", "HbA1c"],
            "dizziness": ["Blood Pressure", "CBC", "ECG", "Blood Glucose"],
            "rash": ["Skin Swab", "Allergy Panel", "CBC"],
            "jaundice": ["Liver Function Tests", "Hepatitis Panel", "Bilirubin"],
            "blood in stool": ["Stool Occult Blood Test", "Colonoscopy referral", "CBC"],
            "blood in urine": ["Urinalysis", "Urine Culture", "Renal Ultrasound"],
        }

        for symptom in symptoms:
            for key, test_list in symptom_test_map.items():
                if key in symptom:
                    tests.update(test_list)

        # Always include basic panel if no tests found
        if not tests:
            tests = {"CBC", "Comprehensive Metabolic Panel (CMP)", "Urinalysis"}

        return list(tests)[:6]

    # ------------------------------------------------------------------ #
    #  JSON Parser                                                         #
    # ------------------------------------------------------------------ #

    def _parse_json_response(self, raw_text: str) -> dict:
        clean = re.sub(r"```(?:json)?|```", "", raw_text).strip()
        try:
            result = json.loads(clean)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM JSON for diagnosis.")
            result = {}

        result.setdefault("conditions", [])
        result.setdefault("risk_level", "unknown")
        result.setdefault("urgency", "routine")
        result.setdefault("reasoning_summary", "")
        result.setdefault("red_flags", [])
        result.setdefault("follow_up_questions", [])
        result.setdefault("recommended_tests", [])
        result.setdefault("differential_notes", "")

        # Validate and cap conditions
        validated = []
        for c in result["conditions"]:
            if isinstance(c, dict):
                validated.append({
                    "name": c.get("name", "Unknown"),
                    "icd10": c.get("icd10", "N/A"),
                    "probability": c.get("probability", "low"),
                    "confidence": c.get("confidence", 0.0),
                    "reasoning": c.get("reasoning", ""),
                    "specialist": c.get("specialist", "General Practitioner"),
                    "urgency": c.get("urgency", "routine"),
                })
        result["conditions"] = validated[:5]

        return result


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_agent_instance = None


async def analyze(
    symptom_data: dict = None,
    symptoms: list = None,
    age: int = None,
    gender: str = None,
) -> dict:
    """Module-level wrapper for medical diagnosis."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = DiagnosisAgent()

    if symptom_data is None and symptoms is not None:
        symptom_data = {"symptoms": symptoms}
        if age is not None:
            symptom_data["patient_age"] = str(age)
        if gender is not None:
            symptom_data["patient_gender"] = gender

    return await _agent_instance.analyze(symptom_data)


async def get_condition_info(condition_name: str) -> dict:
    """Return knowledge-base info for a named condition."""
    return CONDITION_DB.get(condition_name, {})