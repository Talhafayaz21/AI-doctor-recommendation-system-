"""
Recommendation Agent
Maps diagnosed/suspected conditions to appropriate doctor specializations.

Improvements over original:
- 25+ specialties in the mapping (was 10).
- Condition-name AND ICD-10 based specialty lookup.
- Urgency-aware booking guidance (same-day / 48h / 1-week / routine).
- Expanded precautions and first-aid steps per risk level.
- Follow-up questions to ask the doctor — useful for patient preparation.
- Telemedicine suitability flag.
- Diagnostic tests the specialist will likely order (educational).
- Structured LLM prompt returns richer JSON.
"""

import json
import re
import logging
import httpx
from typing import Dict, List, Optional, Tuple
from app.utils.config import settings
from app.utils.prompts import RECOMMENDATION_PROMPT

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Specialty knowledge base
# ─────────────────────────────────────────────────────────────────────────────

# Maps condition keywords / ICD-10 prefixes → specialist info
SPECIALTY_KNOWLEDGE: List[Dict] = [
    {
        "specialty":          "Emergency Medicine Specialist",
        "triggers_name":      ["emergency", "sepsis", "stroke", "heart attack", "anaphylaxis",
                               "haemorrhage", "overdose", "poisoning", "ectopic", "appendicitis",
                               "pulmonary embolism", "meningitis", "subarachnoid"],
        "triggers_icd10":     ["I21", "I63", "I60", "J96", "A41", "O00", "K37", "I26", "G00"],
        "booking_urgency":    "Call emergency services (115 / 1122) immediately",
        "telemedicine":       False,
        "expected_tests":     ["ECG", "Full Blood Count", "CT Brain", "Troponin", "ABG"],
        "follow_up_questions":["What is the immediate treatment plan?", "Will I need admission?"],
    },
    {
        "specialty":          "Cardiologist",
        "triggers_name":      ["cardiac", "cardiology", "myocardial", "angina", "heart failure",
                               
                               "atrial fibrillation", "arrhythmia", "pericarditis", "tachycardia",
                               "deep vein thrombosis", "hypertensive"],
        "triggers_icd10":     ["I", "I20", "I21", "I48", "I50", "I80"],
        "booking_urgency":    "Within 24-48 hours for urgent cardiac symptoms; routine if stable",
        "telemedicine":       False,
        "expected_tests":     ["ECG", "Echocardiogram", "Holter monitor", "Troponin", "BNP"],
        "follow_up_questions":["Do I need a stress test?", "Is my heart rhythm normal?",
                               "What lifestyle changes should I make?"],
    },
    {
        "specialty":          "Pulmonologist",
        "triggers_name":      ["pneumonia", "asthma", "copd", "bronchitis", "pulmonary",
                               "respiratory", "pleural", "tuberculosis"],
        "triggers_icd10":     ["J", "J18", "J45", "J44", "A15"],
        "booking_urgency":    "Within 48 hours for breathing difficulties; routine for stable COPD/asthma",
        "telemedicine":       True,
        "expected_tests":     ["Chest X-Ray", "Spirometry", "Sputum culture", "CT chest", "Peak flow"],
        "follow_up_questions":["Do I need an inhaler?", "Is my lung function normal?",
                               "Do I need a chest X-Ray?"],
    },
    {
        "specialty":          "Neurologist",
        "triggers_name":      ["migraine", "seizure", "epilepsy", "stroke", "tia", "multiple sclerosis",
                               "parkinson", "neuropathy", "meningitis", "brain",
                               "subarachnoid", "vertigo", "tremor"],
        "triggers_icd10":     ["G", "G40", "G43", "G35", "I63", "G45", "G00"],
        "booking_urgency":    "Emergency for stroke/seizure; within 1 week for new neurological symptoms",
        "telemedicine":       False,
        "expected_tests":     ["CT Brain", "MRI Brain", "EEG", "Lumbar puncture", "Nerve conduction study"],
        "follow_up_questions":["Do I need a brain scan?", "Could this be epilepsy?",
                               "Are there medications that could help?"],
    },
    {
        "specialty":          "Gastroenterologist",
        "triggers_name":      ["gerd", "peptic ulcer", "gastroenteritis", "inflammatory bowel",
                               "crohn", "ulcerative colitis", "irritable bowel", "cholecystitis",
                               "pancreatitis", "hepatitis", "colorectal", "appendicitis"],
        "triggers_icd10":     ["K", "K21", "K27", "K58", "K51", "K81", "K85", "B19", "C20"],
        "booking_urgency":    "Emergency for severe abdominal pain; within 1 week for chronic symptoms",
        "telemedicine":       True,
        "expected_tests":     ["Endoscopy", "Colonoscopy", "Abdominal ultrasound", "Liver function tests",
                               "H. pylori test", "Stool analysis"],
        "follow_up_questions":["Do I need an endoscopy?", "Should I change my diet?",
                               "Could this be inflammatory bowel disease?"],
    },
    {
        "specialty":          "Dermatologist",
        "triggers_name":      ["eczema", "psoriasis", "dermatitis", "urticaria", "cellulitis",
                               "melanoma", "acne", "shingles", "tinea", "alopecia",
                               "skin cancer", "rash"],
        "triggers_icd10":     ["L", "L20", "L40", "L50", "L03", "C43", "B02", "B35"],
        "booking_urgency":    "Urgent for spreading cellulitis or suspected melanoma; routine otherwise",
        "telemedicine":       True,
        "expected_tests":     ["Skin biopsy", "Patch testing", "Dermoscopy", "Skin culture",
                               "KOH prep for fungal"],
        "follow_up_questions":["Is this a dangerous skin condition?", "Do I need a biopsy?",
                               "What topical treatment is recommended?"],
    },
    {
        "specialty":          "Orthopaedic Surgeon",
        "triggers_name":      ["fracture", "osteoarthritis", "lumbar disc", "joint replacement",
                               "ligament", "tendon", "sprain", "dislocation", "bone"],
        "triggers_icd10":     ["M80", "M15", "M51", "S"],
        "booking_urgency":    "Emergency for suspected fracture/dislocation; within 1 week for chronic pain",
        "telemedicine":       False,
        "expected_tests":     ["X-Ray", "MRI", "CT scan", "Bone density scan (DEXA)"],
        "follow_up_questions":["Do I need surgery?", "What physiotherapy exercises should I do?",
                               "Do I need a brace or cast?"],
    },
    {
        "specialty":          "Rheumatologist",
        "triggers_name":      ["rheumatoid arthritis", "lupus", "gout", "fibromyalgia",
                               "ankylosing spondylitis", "sjogren", "vasculitis",
                               "polymyalgia", "reactive arthritis"],
        "triggers_icd10":     ["M05", "M32", "M10", "M79.3", "M45"],
        "booking_urgency":    "Within 1–2 weeks for joint inflammation; routine for stable disease",
        "telemedicine":       True,
        "expected_tests":     ["Rheumatoid factor", "ANA", "Anti-CCP", "ESR", "CRP", "Joint X-Ray"],
        "follow_up_questions":["Is this an autoimmune condition?", "What DMARDs might I need?",
                               "Is physical therapy recommended?"],
    },
    {
        "specialty":          "Endocrinologist",
        "triggers_name":      ["diabetes", "thyroid", "hypothyroidism", "hyperthyroidism",
                               "addison", "cushing", "adrenal", "pituitary", "metabolic",
                               "dka", "polycystic ovary"],
        "triggers_icd10":     ["E10", "E11", "E03", "E05", "E24", "E27", "E28.2"],
        "booking_urgency":    "Emergency for DKA; within 1 week for uncontrolled diabetes/thyroid",
        "telemedicine":       True,
        "expected_tests":     ["HbA1c", "Thyroid function tests", "Fasting glucose",
                               "Cortisol levels", "Insulin levels", "Lipid profile"],
        "follow_up_questions":["What are my target blood sugar levels?",
                               "Do I need thyroid medication?",
                               "How often should I monitor my levels?"],
    },
    {
        "specialty":          "Nephrologist",
        "triggers_name":      ["kidney", "renal", "acute renal failure", "chronic kidney disease",
                               "glomerulonephritis", "nephrotic", "polycystic kidney"],
        "triggers_icd10":     ["N17", "N18", "N00", "N04", "Q61"],
        "booking_urgency":    "Emergency for acute renal failure; within 1 week for deteriorating CKD",
        "telemedicine":       True,
        "expected_tests":     ["Renal function tests", "Urinalysis", "Renal ultrasound",
                               "Kidney biopsy", "24h urine protein"],
        "follow_up_questions":["What is my GFR?", "Do I need dialysis?",
                               "What diet should I follow?"],
    },
    {
        "specialty":          "Urologist",
        "triggers_name":      ["urinary tract", "bladder", "prostate", "kidney stones",
                               "nephrolithiasis", "erectile dysfunction", "urinary retention",
                               "bladder cancer", "testicular"],
        "triggers_icd10":     ["N39.0", "N40", "N20", "N10", "C67", "N41", "N45"],
        "booking_urgency":    "Urgent for urinary retention or haematuria; routine for BPH/UTI",
        "telemedicine":       True,
        "expected_tests":     ["Urinalysis", "PSA", "Renal & bladder ultrasound",
                               "Cystoscopy", "Urine cytology"],
        "follow_up_questions":["Do I need a cystoscopy?", "Is this a kidney stone?",
                               "Do I need surgery?"],
    },
    {
        "specialty":          "Gynaecologist / Obstetrician",
        "triggers_name":      ["pelvic inflammatory", "endometriosis", "polycystic ovary",
                               "ectopic pregnancy", "fibroid", "menstrual", "vaginal",
                               "cervical", "ovarian", "breast cancer", "pregnancy"],
        "triggers_icd10":     ["N73", "N80", "E28.2", "O00", "D25", "C50", "N92"],
        "booking_urgency":    "Emergency for ectopic pregnancy; within 48h for severe PID; routine otherwise",
        "telemedicine":       False,
        "expected_tests":     ["Pelvic ultrasound", "Pap smear", "Beta-hCG", "STI screen",
                               "Endometrial biopsy", "Mammogram"],
        "follow_up_questions":["Is this a hormonal issue?", "Could I be pregnant?",
                               "Do I need a pelvic ultrasound?"],
    },
    {
        "specialty":          "Psychiatrist",
        "triggers_name":      ["depression", "anxiety", "panic", "bipolar", "schizophrenia",
                               "ptsd", "psychosis", "hallucinations", "suicidal",
                               "self-harm", "eating disorder", "ocd", "adhd"],
        "triggers_icd10":     ["F20", "F31", "F32", "F40", "F41", "F43", "F50", "F90"],
        "booking_urgency":    "Emergency for suicidal ideation/psychosis; within 1 week otherwise",
        "telemedicine":       True,
        "expected_tests":     ["Psychiatric evaluation", "PHQ-9", "GAD-7",
                               "Cognitive assessment", "Thyroid function (to exclude organic cause)"],
        "follow_up_questions":["Do I need medication?", "What therapy is recommended?",
                               "Is hospitalisation needed?"],
    },
    {
        "specialty":          "Paediatrician",
        "triggers_name":      ["child", "infant", "baby", "neonate", "developmental delay",
                               "failure to thrive", "vaccination", "paediatric"],
        "triggers_icd10":     ["Z00.1", "F80", "F81", "F82", "P"],
        "booking_urgency":    "Same day for febrile infants <3 months; routine otherwise",
        "telemedicine":       True,
        "expected_tests":     ["Full Blood Count", "CRP", "Growth chart review",
                               "Developmental screening", "Urinalysis"],
        "follow_up_questions":["Is this normal for their age?", "Do they need vaccinations?",
                               "Is their growth and development on track?"],
    },
    {
        "specialty":          "Infectious Disease Specialist",
        "triggers_name":      ["malaria", "dengue", "typhoid", "tuberculosis", "sepsis",
                               "hiv", "aids", "mononucleosis", "hepatitis", "parasites",
                               "tropical fever"],
        "triggers_icd10":     ["A", "B", "A50", "B50", "A90", "A01", "A15", "B27", "A41"],
        "booking_urgency":    "Emergency for sepsis; within 48h for tropical fevers; routine otherwise",
        "telemedicine":       False,
        "expected_tests":     ["Blood culture", "Malaria RDT / smear", "HIV test",
                               "Dengue NS1 antigen", "Widal test", "PCR panel"],
        "follow_up_questions":["Do I need isolation?", "Is this contagious?",
                               "What antibiotic / antiviral is recommended?"],
    },
    {
        "specialty":          "Oncologist",
        "triggers_name":      ["cancer", "malignancy", "tumour", "tumor", "lymphoma",
                               "leukaemia", "leukemia", "melanoma", "carcinoma", "metastasis"],
        "triggers_icd10":     ["C"],
        "booking_urgency":    "Within 48-72 hours for suspected new cancer",
        "telemedicine":       False,
        "expected_tests":     ["Biopsy", "CT PET scan", "Tumour markers", "Full blood count",
                               "Bone marrow biopsy if haematological"],
        "follow_up_questions":["What stage is this?", "What treatment options are available?",
                               "Should I see a specialist cancer team?"],
    },
    {
        "specialty":          "Haematologist",
        "triggers_name":      ["anaemia", "anemia", "sickle cell", "thalassemia", "haemophilia",
                               "bleeding disorder", "thrombocytopenia", "leukaemia", "lymphoma"],
        "triggers_icd10":     ["D50", "D57", "D56", "D66", "D69", "C91", "C85"],
        "booking_urgency":    "Within 48h for active bleeding/haematological emergency; routine otherwise",
        "telemedicine":       True,
        "expected_tests":     ["Full Blood Count", "Blood film", "Coagulation screen",
                               "Iron studies", "Vitamin B12 / Folate", "Bone marrow biopsy"],
        "follow_up_questions":["What is my haemoglobin level?", "Do I have a clotting disorder?",
                               "Do I need a transfusion?"],
    },
    {
        "specialty":          "Ophthalmologist",
        "triggers_name":      ["vision loss", "blurred vision", "eye pain", "eye redness",
                               "glaucoma", "cataract", "retina", "macular degeneration",
                               "double vision", "corneal"],
        "triggers_icd10":     ["H"],
        "booking_urgency":    "Emergency for sudden vision loss; within 24h for painful red eye",
        "telemedicine":       False,
        "expected_tests":     ["Visual acuity", "Slit lamp exam", "Intraocular pressure",
                               "Fundoscopy", "OCT retinal scan"],
        "follow_up_questions":["Is my vision at risk?", "Do I need glasses or surgery?",
                               "Is this glaucoma?"],
    },
    {
        "specialty":          "ENT (Ear, Nose & Throat) Specialist",
        "triggers_name":      ["tinnitus", "hearing loss", "ear pain", "sore throat",
                               "hoarseness", "nasal polyp", "sinusitis", "vertigo",
                               "sleep apnea", "tonsillitis", "laryngitis"],
        "triggers_icd10":     ["H60", "H81", "J32", "J35", "H90", "J38", "G47.3"],
        "booking_urgency":    "Within 48h for sudden hearing loss; routine otherwise",
        "telemedicine":       True,
        "expected_tests":     ["Audiometry", "Tympanometry", "Nasal endoscopy",
                               "CT sinuses", "Laryngoscopy"],
        "follow_up_questions":["Do I have an ear infection?", "Is surgery needed for my tonsils?",
                               "Could this be sinusitis?"],
    },
    {
        "specialty":          "General Practitioner (GP)",
        "triggers_name":      [],  # Default fallback
        "triggers_icd10":     [],
        "booking_urgency":    "Within a few days for non-urgent symptoms",
        "telemedicine":       True,
        "expected_tests":     ["Full Blood Count", "Basic metabolic panel", "Urinalysis",
                               "Blood pressure", "BMI"],
        "follow_up_questions":["What investigations do I need?",
                               "Do I need a referral to a specialist?",
                               "Are there lifestyle changes I should make?"],
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Risk-level guidance
# ─────────────────────────────────────────────────────────────────────────────

RISK_GUIDANCE: Dict[str, Dict] = {
    "critical": {
        "precautions": [
            "Call emergency services (115 / 1122) or go to the nearest ER IMMEDIATELY.",
            "Do not drive yourself — call an ambulance or have someone take you.",
            "Do not eat or drink anything until assessed by a doctor.",
            "Stay calm; lie down if you feel faint.",
            "Inform someone nearby about your condition.",
        ],
        "first_aid_steps": [
            "Call 115 / 1122 immediately.",
            "Do not leave the patient alone at any time.",
            "If unconscious and not breathing: begin CPR if trained.",
            "If allergic reaction: administer epinephrine (EpiPen) if available.",
            "Keep airway clear and patient in recovery position if unconscious.",
        ],
    },
    "high": {
        "precautions": [
            "Seek medical attention today — visit a clinic or urgent care centre.",
            "Avoid strenuous activity or exertion.",
            "Do not ignore worsening symptoms — go to ER if they escalate.",
            "Keep an emergency contact nearby.",
            "Do not self-medicate with prescription drugs without guidance.",
        ],
        "first_aid_steps": [
            "Rest immediately and avoid physical exertion.",
            "Stay well-hydrated with clear fluids unless told otherwise.",
            "Monitor vital signs if possible (pulse, temperature, breathing).",
            "Take prescribed medications as directed.",
            "Note symptom changes to report to the doctor.",
        ],
    },
    "medium": {
        "precautions": [
            "Schedule a medical consultation within the next 48–72 hours.",
            "Monitor symptoms closely and note any changes.",
            "Maintain adequate rest and hydration.",
            "Avoid known triggers or activities that worsen symptoms.",
            "Do not self-medicate beyond basic OTC remedies without advice.",
        ],
        "first_aid_steps": [
            "Get adequate rest — 7–9 hours sleep.",
            "Stay hydrated: 2–3 litres of water per day.",
            "Take paracetamol/ibuprofen for fever or pain as directed on the label.",
            "Eat light, easily digestible meals.",
            "Track your temperature twice daily and note trends.",
        ],
    },
    "low": {
        "precautions": [
            "Continue to monitor symptoms over the next few days.",
            "Maintain healthy lifestyle habits: sleep, hydration, and nutrition.",
            "See a GP if symptoms persist beyond 5–7 days or worsen.",
            "Avoid sharing utensils or close contact if an infection is suspected.",
        ],
        "first_aid_steps": [
            "Rest as needed.",
            "Drink plenty of fluids.",
            "Over-the-counter remedies (antihistamines, decongestants, pain relief) as appropriate.",
            "Warm salt-water gargles for sore throat.",
            "Cool compress for fever or headache.",
        ],
    },
}

GENERAL_LIFESTYLE_ADVICE: List[str] = [
    "Follow up with your healthcare provider if symptoms persist or worsen.",
    "Avoid self-medicating with prescription antibiotics or steroids.",
    "Keep a symptom diary to share with your doctor.",
    "Ensure your vaccinations are up to date.",
    "Practise good hand hygiene to prevent spreading infection.",
]


class RecommendationAgent:
    """Agent responsible for recommending appropriate medical specialists."""

    def __init__(self):
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.model   = settings.OPENAI_MODEL
        self.api_key = settings.OPENAI_API_KEY

        # Check if API key is properly set (not placeholder)
        if self.api_key and ("your-" in self.api_key.lower() or "here" in self.api_key.lower()):
            logger.warning("OpenAI API key appears to be placeholder - using fallback mode")
            self.api_key = None

    async def recommend(self, diagnosis_data: dict, symptom_data: dict) -> dict:
        """
        Recommend appropriate specialist(s) and provide actionable guidance.

        Returns:
            dict with keys:
                recommended_specialist      – str
                alternative_specialists     – list[str]
                booking_urgency             – str
                telemedicine_suitable       – bool
                precautions                 – list[str]
                first_aid_steps             – list[str]
                expected_tests              – list[str]
                follow_up_questions         – list[str]
                lifestyle_advice            – list[str]
        """
        input_summary = self._build_input_summary(diagnosis_data, symptom_data)

        payload = {
            "model": self.model,
            "max_tokens": 1500,
            "messages": [
                {"role": "system", "content": RECOMMENDATION_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Based on the following, return ONLY valid JSON with these keys:\n"
                        "  recommended_specialist (string)\n"
                        "  alternative_specialists (list of strings)\n"
                        "  booking_urgency (string)\n"
                        "  telemedicine_suitable (boolean)\n"
                        "  precautions (list of strings)\n"
                        "  first_aid_steps (list of strings)\n"
                        "  expected_tests (list of strings)\n"
                        "  follow_up_questions (list of strings)\n"
                        "  lifestyle_advice (list of strings)\n\n"
                        f"{input_summary}"
                    ),
                },
            ],
            "temperature": 0.3,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }

        # Check if API key is available
        if not self.api_key:
            logger.info("OpenAI API key not available - using local recommendation")
            return self._local_recommendation(diagnosis_data, symptom_data)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            raw_text = data["choices"][0]["message"]["content"]
            result   = self._parse_json_response(raw_text)

            # Enrich with local knowledge where LLM left gaps
            local = self._local_recommendation(diagnosis_data, symptom_data)
            return self._merge(result, local)

        except Exception as e:
            logger.warning(f"OpenAI API failed for recommendations: {e}. Using fallback.")
            return self._local_recommendation(diagnosis_data, symptom_data)

    # ------------------------------------------------------------------ #
    #  Local recommendation engine                                        #
    # ------------------------------------------------------------------ #

    def _local_recommendation(self, diagnosis_data: dict, symptom_data: dict) -> dict:
        conditions  = diagnosis_data.get("conditions", [])
        risk_level  = diagnosis_data.get("risk_level", "medium").lower()
        symptoms    = symptom_data.get("symptoms", [])
        symptom_str = " ".join(symptoms).lower()

        # Build candidate list: (score, specialty_info)
        candidates: List[Tuple[int, Dict]] = []
        for sp in SPECIALTY_KNOWLEDGE:
            score = 0
            for cond in conditions:
                name = cond.get("name",  "").lower()
                icd  = cond.get("icd10", "").upper()
                score += sum(2 for t in sp["triggers_name"]  if t in name)
                score += sum(3 for t in sp["triggers_icd10"] if icd.startswith(t))
            score += sum(1 for t in sp["triggers_name"] if t in symptom_str)
            if score > 0:
                candidates.append((score, sp))

        candidates.sort(key=lambda x: x[0], reverse=True)

        if candidates:
            primary   = candidates[0][1]
            alts      = [sp["specialty"] for _, sp in candidates[1:4]
                         if sp["specialty"] != primary["specialty"]]
        else:
            primary   = next(sp for sp in SPECIALTY_KNOWLEDGE
                              if sp["specialty"].startswith("General Practitioner"))
            alts      = []

        guidance = RISK_GUIDANCE.get(risk_level, RISK_GUIDANCE["medium"])

        return {
            "recommended_specialist":  primary["specialty"],
            "alternative_specialists": alts[:2],
            "booking_urgency":         primary["booking_urgency"],
            "telemedicine_suitable":   primary["telemedicine"],
            "precautions":             guidance["precautions"],
            "first_aid_steps":         guidance["first_aid_steps"],
            "expected_tests":          primary["expected_tests"],
            "follow_up_questions":     primary["follow_up_questions"],
            "lifestyle_advice":        GENERAL_LIFESTYLE_ADVICE,
        }

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #

    def _build_input_summary(self, diagnosis_data: dict, symptom_data: dict) -> str:
        conditions    = diagnosis_data.get("conditions", [])
        risk_level    = diagnosis_data.get("risk_level", "unknown")
        red_flags     = diagnosis_data.get("red_flags",  [])
        symptoms      = ", ".join(symptom_data.get("symptoms",   [])) or "none"
        body_parts    = ", ".join(symptom_data.get("body_parts", [])) or "unspecified"
        ctx           = symptom_data.get("patient_context", {}) or {}
        cond_lines    = "\n".join(
            f"  - {c.get('name')} (ICD: {c.get('icd10','?')}, urgency: {c.get('urgency','?')})"
            for c in conditions if isinstance(c, dict)
        ) or "  undetermined"

        return (
            f"Possible conditions:\n{cond_lines}\n"
            f"Risk level: {risk_level}\n"
            f"Red flags: {', '.join(red_flags) or 'none'}\n"
            f"Symptoms: {symptoms}\n"
            f"Body parts affected: {body_parts}\n"
            f"Patient age: {ctx.get('age', 'unknown')}\n"
            f"Patient gender: {ctx.get('gender', 'unknown')}\n"
            f"Chronic conditions: {', '.join(ctx.get('chronic_conditions', [])) or 'none'}"
        )

    def _merge(self, api: dict, local: dict) -> dict:
        merged = dict(api)
        if not merged.get("recommended_specialist"):
            merged["recommended_specialist"]  = local["recommended_specialist"]
        if not merged.get("alternative_specialists"):
            merged["alternative_specialists"] = local["alternative_specialists"]
        if not merged.get("booking_urgency"):
            merged["booking_urgency"]         = local["booking_urgency"]
        if "telemedicine_suitable" not in merged:
            merged["telemedicine_suitable"]   = local["telemedicine_suitable"]
        if not merged.get("precautions"):
            merged["precautions"]             = local["precautions"]
        if not merged.get("first_aid_steps"):
            merged["first_aid_steps"]         = local["first_aid_steps"]
        if not merged.get("expected_tests"):
            merged["expected_tests"]          = local["expected_tests"]
        if not merged.get("follow_up_questions"):
            merged["follow_up_questions"]     = local["follow_up_questions"]
        if not merged.get("lifestyle_advice"):
            merged["lifestyle_advice"]        = local["lifestyle_advice"]
        return merged

    def _parse_json_response(self, raw_text: str) -> dict:
        clean = re.sub(r"```(?:json)?|```", "", raw_text).strip()
        try:
            result = json.loads(clean)
        except json.JSONDecodeError:
            result = {}

        result.setdefault("recommended_specialist",  "General Practitioner")
        result.setdefault("alternative_specialists", [])
        result.setdefault("booking_urgency",         "Within a few days")
        result.setdefault("telemedicine_suitable",   True)
        result.setdefault("precautions",             [])
        result.setdefault("first_aid_steps",         [])
        result.setdefault("expected_tests",          [])
        result.setdefault("follow_up_questions",     [])
        result.setdefault("lifestyle_advice",        [])
        return result


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────

_agent_instance: Optional[RecommendationAgent] = None


async def recommend(diagnosis_data: dict, symptom_data: dict) -> dict:
    """Module-level wrapper – maintains a singleton RecommendationAgent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = RecommendationAgent()
    return await _agent_instance.recommend(diagnosis_data, symptom_data)