from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum


# ──────────────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────────────

class DoctorSpecialty(str, Enum):
    CARDIOLOGY          = "Cardiology"
    PULMONOLOGY         = "Pulmonology"
    GASTROENTEROLOGY    = "Gastroenterology"
    NEUROLOGY           = "Neurology"
    DERMATOLOGY         = "Dermatology"
    ORTHOPEDICS         = "Orthopedics"
    ENDOCRINOLOGY       = "Endocrinology"
    PSYCHIATRY          = "Psychiatry"
    PEDIATRICS          = "Pediatrics"
    GENERAL_PRACTICE    = "General Practice"
    URGENT_CARE         = "Urgent Care"
    EMERGENCY_MEDICINE  = "Emergency Medicine"
    ONCOLOGY            = "Oncology"
    RADIOLOGY           = "Radiology"
    PATHOLOGY           = "Pathology"
    ANESTHESIOLOGY      = "Anesthesiology"
    OBSTETRICS          = "Obstetrics"
    GYNECOLOGY          = "Gynecology"
    UROLOGY             = "Urology"
    OPHTHALMOLOGY       = "Ophthalmology"
    OTOLARYNGOLOGY      = "Otolaryngology"
    NEPHROLOGY          = "Nephrology"
    HEPATOLOGY          = "Hepatology"
    INFECTIOUS_DISEASE  = "Infectious Disease"
    RHEUMATOLOGY        = "Rheumatology"
    HEMATOLOGY          = "Hematology"
    IMMUNOLOGY          = "Immunology"


class AppointmentStatus(str, Enum):
    SCHEDULED   = "scheduled"
    CONFIRMED   = "confirmed"
    COMPLETED   = "completed"
    CANCELLED   = "cancelled"
    NO_SHOW     = "no_show"


# ──────────────────────────────────────────────────────────────────────────────
# Disease → Specialty Mapping  (used by the Recommendation Agent)
# ──────────────────────────────────────────────────────────────────────────────

DISEASE_SPECIALTY_MAP: Dict[str, Dict] = {
    # Cardiovascular
    "Hypertension":         {"primary": "Cardiology",       "alternative": ["General Practice", "Nephrology"]},
    "Heart Attack":         {"primary": "Cardiology",       "alternative": ["Emergency Medicine"]},
    "Coronary Artery Disease": {"primary": "Cardiology",   "alternative": ["Cardiology"]},
    "Arrhythmia":           {"primary": "Cardiology",       "alternative": ["General Practice"]},

    # Respiratory
    "Asthma":               {"primary": "Pulmonology",      "alternative": ["General Practice", "Immunology"]},
    "Pneumonia":            {"primary": "Pulmonology",      "alternative": ["Infectious Disease", "General Practice"]},
    "Tuberculosis":         {"primary": "Pulmonology",      "alternative": ["Infectious Disease"]},
    "COVID-19":             {"primary": "Infectious Disease","alternative": ["Pulmonology", "General Practice"]},
    "Bronchitis":           {"primary": "Pulmonology",      "alternative": ["General Practice"]},

    # Gastrointestinal
    "Gastroenteritis":      {"primary": "Gastroenterology", "alternative": ["General Practice", "Infectious Disease"]},
    "Hepatitis A":          {"primary": "Hepatology",       "alternative": ["Gastroenterology", "Infectious Disease"]},
    "Hepatitis B":          {"primary": "Hepatology",       "alternative": ["Gastroenterology"]},
    "Hepatitis C":          {"primary": "Hepatology",       "alternative": ["Gastroenterology"]},
    "Typhoid":              {"primary": "Infectious Disease","alternative": ["Gastroenterology", "General Practice"]},
    "Peptic Ulcer":         {"primary": "Gastroenterology", "alternative": ["General Practice"]},
    "Irritable Bowel Syndrome": {"primary": "Gastroenterology", "alternative": ["General Practice"]},

    # Endocrine / Metabolic
    "Diabetes":             {"primary": "Endocrinology",    "alternative": ["General Practice", "Nephrology"]},
    "Thyroid Disorder":     {"primary": "Endocrinology",    "alternative": ["General Practice"]},

    # Neurological
    "Migraine":             {"primary": "Neurology",        "alternative": ["General Practice"]},
    "Epilepsy":             {"primary": "Neurology",        "alternative": ["General Practice"]},
    "Stroke":               {"primary": "Neurology",        "alternative": ["Emergency Medicine"]},

    # Infectious
    "Malaria":              {"primary": "Infectious Disease","alternative": ["General Practice", "Hematology"]},
    "Dengue":               {"primary": "Infectious Disease","alternative": ["General Practice", "Hematology"]},
    "Chickenpox":           {"primary": "Dermatology",      "alternative": ["Infectious Disease", "General Practice"]},
    "Urinary Tract Infection": {"primary": "Urology",       "alternative": ["Nephrology", "General Practice"]},

    # Dermatological
    "Psoriasis":            {"primary": "Dermatology",      "alternative": ["Rheumatology"]},
    "Eczema":               {"primary": "Dermatology",      "alternative": ["Immunology", "General Practice"]},

    # Musculoskeletal
    "Arthritis":            {"primary": "Rheumatology",     "alternative": ["Orthopedics", "General Practice"]},
    "Osteoporosis":         {"primary": "Orthopedics",      "alternative": ["Endocrinology", "Rheumatology"]},

    # Mental Health
    "Anxiety Disorder":     {"primary": "Psychiatry",       "alternative": ["General Practice", "Neurology"]},
    "Depression":           {"primary": "Psychiatry",       "alternative": ["General Practice", "Neurology"]},

    # Renal
    "Kidney Disease":       {"primary": "Nephrology",       "alternative": ["Urology", "General Practice"]},

    # Children
    "Common Cold":          {"primary": "General Practice", "alternative": ["Pediatrics", "Otolaryngology"]},
    "Influenza":            {"primary": "General Practice", "alternative": ["Infectious Disease", "Pulmonology"]},
}


def get_specialty_for_disease(disease_name: str) -> Dict:
    """
    Return primary and alternative specialties for a given disease name.
    Falls back to General Practice for unknown diseases.
    """
    key = disease_name.strip()
    # Exact match first
    if key in DISEASE_SPECIALTY_MAP:
        return DISEASE_SPECIALTY_MAP[key]
    # Case-insensitive partial match
    key_lower = key.lower()
    for disease, mapping in DISEASE_SPECIALTY_MAP.items():
        if key_lower in disease.lower() or disease.lower() in key_lower:
            return mapping
    # Default fallback
    return {"primary": "General Practice", "alternative": ["Urgent Care"]}


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────────────────────────────────────

class Doctor(BaseModel):
    id:                 str
    name:               str
    specialty:          DoctorSpecialty
    sub_specialty:      Optional[str]            = None
    location:           str
    city:               str
    hospital:           str
    rating:             float = Field(ge=1.0, le=5.0)
    experience_years:   int
    languages:          List[str]
    insurance_accepted: List[str]
    available_slots:    int
    consultation_fee:   int                      # PKR
    bio:                Optional[str]            = None
    education:          Optional[str]            = None
    certifications:     Optional[List[str]]      = None
    phone:              Optional[str]            = None
    telemedicine:       bool                     = False


class DoctorAvailability(BaseModel):
    doctor_id:    str
    date:         str
    time_slots:   List[str]
    is_available: bool


class Appointment(BaseModel):
    id:         str
    doctor_id:  str
    patient_id: str
    date:       str
    time:       str
    reason:     str
    symptoms:   Optional[List[str]] = None
    status:     AppointmentStatus   = AppointmentStatus.SCHEDULED
    notes:      Optional[str]       = None
    created_at: str
    updated_at: Optional[str]       = None


class DoctorRecommendation(BaseModel):
    """Returned by the Recommendation Agent to the frontend."""
    disease:               str
    primary_specialty:     str
    alternative_specialty: List[str]
    recommended_doctors:   List[Doctor]
    urgency:               str   # "normal" | "urgent" | "emergency"
    advice:                str
    