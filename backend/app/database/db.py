"""
backend/database/db.py
======================
Pakistani doctor database (100+ doctors) with full recommendation engine.

Cities covered:
    Islamabad, Karachi, Lahore, Rawalpindi, Peshawar,
    Quetta, Multan, Faisalabad, Hyderabad, Sialkot

Specialties: 20+ medical specialties mapped to diseases.

Public API
----------
    get_doctor_by_id(doctor_id)          → Optional[Dict]
    get_doctors_by_specialty(specialty)  → List[Dict]
    get_doctors_by_city(city)            → List[Dict]
    recommend_doctors(disease, city, top_k)  → Dict  ← main recommendation entry
    create_appointment(data)             → Dict
    get_patient_appointments(patient_id) → List[Dict]
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .doctor_schema import (
    DISEASE_SPECIALTY_MAP,
    get_specialty_for_disease,
    AppointmentStatus,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# 100+ PAKISTANI DOCTORS DATABASE
# ══════════════════════════════════════════════════════════════════════════════

MOCK_DATABASE: Dict[str, Any] = {

    # ── Appointments (start empty) ─────────────────────────────────────────
    "appointments": [],

    # ── Patients ───────────────────────────────────────────────────────────
    "patients": [
        {
            "id": "pat_001", "name": "Ahmed Khan", "age": 42,
            "gender": "Male", "city": "Islamabad",
            "email": "ahmed.khan@gmail.com", "phone": "+92-300-1234567",
        },
        {
            "id": "pat_002", "name": "Fatima Malik", "age": 29,
            "gender": "Female", "city": "Lahore",
            "email": "fatima.m@gmail.com", "phone": "+92-321-9876543",
        },
    ],

    # ── Doctors ─────────────────────────────────────────────────────────────
    "doctors": [

        # ────────────────── CARDIOLOGY ──────────────────────────────────────
        {
            "id": "doc_001", "name": "Dr. Syed Zubair Ahmed",
            "specialty": "Cardiology", "sub_specialty": "Interventional Cardiology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Pakistan Institute of Medical Sciences (PIMS)",
            "rating": 4.9, "experience_years": 20,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health", "EFU Health"],
            "available_slots": 4, "consultation_fee": 3000,
            "education": "MBBS (KEMU), FCPS Cardiology",
            "certifications": ["FCPS", "FRCP London"],
            "phone": "+92-51-9260800", "telemedicine": True,
        },
        {
            "id": "doc_002", "name": "Dr. Nadeem Qamar",
            "specialty": "Cardiology", "sub_specialty": "Echocardiography",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Aga Khan University Hospital",
            "rating": 4.8, "experience_years": 18,
            "languages": ["Urdu", "English", "Sindhi"],
            "insurance_accepted": ["Jubilee Health", "Allianz EFU", "Adamjee"],
            "available_slots": 3, "consultation_fee": 4500,
            "education": "MBBS, FCPS Cardiology, FACC (USA)",
            "certifications": ["FCPS", "FACC", "FESC"],
            "phone": "+92-21-34930051", "telemedicine": True,
        },
        {
            "id": "doc_003", "name": "Dr. Pervez Akbar",
            "specialty": "Cardiology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Services Hospital Lahore",
            "rating": 4.7, "experience_years": 16,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "EFU Health"],
            "available_slots": 5, "consultation_fee": 2500,
            "education": "MBBS (KEMU), FCPS Cardiology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_004", "name": "Dr. Salma Hussain",
            "specialty": "Cardiology",
            "city": "Rawalpindi", "location": "Rawalpindi, Pakistan",
            "hospital": "Holy Family Hospital",
            "rating": 4.6, "experience_years": 14,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "State Life"],
            "available_slots": 6, "consultation_fee": 2000,
            "education": "MBBS, MRCP (UK), FCPS Cardiology",
            "certifications": ["FCPS", "MRCP"], "telemedicine": True,
        },
        {
            "id": "doc_005", "name": "Dr. Tariq Masood",
            "specialty": "Cardiology",
            "city": "Faisalabad", "location": "Faisalabad, Pakistan",
            "hospital": "Allied Hospital Faisalabad",
            "rating": 4.5, "experience_years": 12,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "EFU Health"],
            "available_slots": 7, "consultation_fee": 1800,
            "education": "MBBS (UHS), FCPS Cardiology",
            "certifications": ["FCPS"], "telemedicine": False,
        },

        # ────────────────── PULMONOLOGY ─────────────────────────────────────
        {
            "id": "doc_006", "name": "Dr. Muhammad Irfan",
            "specialty": "Pulmonology", "sub_specialty": "Tuberculosis & Chest Diseases",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Gulab Devi Chest Hospital",
            "rating": 4.9, "experience_years": 22,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health", "EFU Health"],
            "available_slots": 3, "consultation_fee": 2000,
            "education": "MBBS, FCPS Pulmonology",
            "certifications": ["FCPS", "MRCP"], "telemedicine": True,
        },
        {
            "id": "doc_007", "name": "Dr. Javaid Khan",
            "specialty": "Pulmonology",
            "city": "Peshawar", "location": "Peshawar, Pakistan",
            "hospital": "Lady Reading Hospital",
            "rating": 4.7, "experience_years": 17,
            "languages": ["Urdu", "English", "Pashto"],
            "insurance_accepted": ["State Life", "EFU Health"],
            "available_slots": 5, "consultation_fee": 1500,
            "education": "MBBS (KMU), FCPS Pulmonology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_008", "name": "Dr. Ayesha Raza",
            "specialty": "Pulmonology",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Jinnah Postgraduate Medical Centre (JPMC)",
            "rating": 4.8, "experience_years": 15,
            "languages": ["Urdu", "English", "Sindhi"],
            "insurance_accepted": ["Jubilee Health", "Allianz EFU"],
            "available_slots": 4, "consultation_fee": 2500,
            "education": "MBBS, FCPS Pulmonology",
            "certifications": ["FCPS", "FRCPC"], "telemedicine": True,
        },
        {
            "id": "doc_009", "name": "Dr. Riaz Ahmed",
            "specialty": "Pulmonology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Shifa International Hospital",
            "rating": 4.6, "experience_years": 13,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 6, "consultation_fee": 3500,
            "education": "MBBS (SZABMU), FCPS Pulmonology",
            "certifications": ["FCPS"], "telemedicine": True,
        },

        # ────────────────── GASTROENTEROLOGY ────────────────────────────────
        {
            "id": "doc_010", "name": "Dr. Wasim Jafri",
            "specialty": "Gastroenterology", "sub_specialty": "Hepatology",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Aga Khan University Hospital",
            "rating": 4.9, "experience_years": 25,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "Allianz EFU", "Adamjee"],
            "available_slots": 2, "consultation_fee": 5000,
            "education": "MBBS, FRCP (London), FACG (USA)",
            "certifications": ["FRCP", "FACG", "AGAF"], "telemedicine": True,
        },
        {
            "id": "doc_011", "name": "Dr. Zafar Iqbal",
            "specialty": "Gastroenterology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Shaukat Khanum Memorial Cancer Hospital",
            "rating": 4.8, "experience_years": 19,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 4, "consultation_fee": 3000,
            "education": "MBBS, FCPS Gastroenterology",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_012", "name": "Dr. Khalid Nawaz",
            "specialty": "Gastroenterology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Capital Hospital CDA",
            "rating": 4.6, "experience_years": 14,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "EFU Health"],
            "available_slots": 5, "consultation_fee": 2500,
            "education": "MBBS (NUMS), FCPS Gastroenterology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_013", "name": "Dr. Lubna Kamani",
            "specialty": "Gastroenterology",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "South City Hospital",
            "rating": 4.7, "experience_years": 16,
            "languages": ["Urdu", "English", "Sindhi", "Gujarati"],
            "insurance_accepted": ["Jubilee Health", "EFU Health"],
            "available_slots": 6, "consultation_fee": 3500,
            "education": "MBBS, FCPS Gastroenterology",
            "certifications": ["FCPS"], "telemedicine": True,
        },

        # ────────────────── NEUROLOGY ────────────────────────────────────────
        {
            "id": "doc_014", "name": "Dr. Rashid Jooma",
            "specialty": "Neurology", "sub_specialty": "Neurosurgery",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Aga Khan University Hospital",
            "rating": 4.9, "experience_years": 28,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "Allianz EFU", "Adamjee"],
            "available_slots": 2, "consultation_fee": 6000,
            "education": "MBBS, FRCS (UK), FRCSC",
            "certifications": ["FRCS", "FRCSC"], "telemedicine": True,
        },
        {
            "id": "doc_015", "name": "Dr. Mohammad Wasay",
            "specialty": "Neurology",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Aga Khan University Hospital",
            "rating": 4.8, "experience_years": 20,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "Allianz EFU"],
            "available_slots": 3, "consultation_fee": 5000,
            "education": "MBBS, FCPS Neurology, FAAN (USA)",
            "certifications": ["FCPS", "FAAN"], "telemedicine": True,
        },
        {
            "id": "doc_016", "name": "Dr. Azra Zuberi",
            "specialty": "Neurology", "sub_specialty": "Pediatric Neurology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Children's Hospital Lahore",
            "rating": 4.8, "experience_years": 18,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 4, "consultation_fee": 3000,
            "education": "MBBS, FCPS Neurology",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_017", "name": "Dr. Nauman Tariq",
            "specialty": "Neurology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Shifa International Hospital",
            "rating": 4.7, "experience_years": 15,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "Jubilee Health", "EFU Health"],
            "available_slots": 5, "consultation_fee": 4000,
            "education": "MBBS, FCPS Neurology",
            "certifications": ["FCPS", "MRCP"], "telemedicine": True,
        },

        # ────────────────── ENDOCRINOLOGY (Diabetes & Thyroid) ───────────────
        {
            "id": "doc_018", "name": "Dr. Abdul Basit",
            "specialty": "Endocrinology", "sub_specialty": "Diabetes Management",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Baqai Institute of Diabetology & Endocrinology",
            "rating": 4.9, "experience_years": 24,
            "languages": ["Urdu", "English", "Sindhi"],
            "insurance_accepted": ["Jubilee Health", "State Life", "EFU Health"],
            "available_slots": 3, "consultation_fee": 3500,
            "education": "MBBS, FRCP (UK)",
            "certifications": ["FRCP", "FACE (USA)"], "telemedicine": True,
        },
        {
            "id": "doc_019", "name": "Dr. Bilal Bin Younus",
            "specialty": "Endocrinology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Shaukat Khanum Memorial Cancer Hospital",
            "rating": 4.7, "experience_years": 14,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 5, "consultation_fee": 2500,
            "education": "MBBS (KEMU), FCPS Endocrinology",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_020", "name": "Dr. Rubina Hussain",
            "specialty": "Endocrinology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "PIMS Hospital",
            "rating": 4.6, "experience_years": 13,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "EFU Health"],
            "available_slots": 6, "consultation_fee": 2000,
            "education": "MBBS (SZABMU), FCPS Endocrinology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_021", "name": "Dr. Saira Waqas",
            "specialty": "Endocrinology",
            "city": "Rawalpindi", "location": "Rawalpindi, Pakistan",
            "hospital": "Rawalpindi Medical University Hospital",
            "rating": 4.5, "experience_years": 10,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life"],
            "available_slots": 7, "consultation_fee": 1800,
            "education": "MBBS, FCPS Endocrinology",
            "certifications": ["FCPS"], "telemedicine": True,
        },

        # ────────────────── INFECTIOUS DISEASE ──────────────────────────────
        {
            "id": "doc_022", "name": "Dr. Fatima Mir",
            "specialty": "Infectious Disease", "sub_specialty": "Tropical Medicine",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Indus Hospital",
            "rating": 4.8, "experience_years": 17,
            "languages": ["Urdu", "English", "Sindhi"],
            "insurance_accepted": ["Jubilee Health", "EFU Health"],
            "available_slots": 4, "consultation_fee": 2500,
            "education": "MBBS, FCPS Infectious Disease",
            "certifications": ["FCPS", "DTM&H"], "telemedicine": True,
        },
        {
            "id": "doc_023", "name": "Dr. Aslam Khan",
            "specialty": "Infectious Disease",
            "city": "Peshawar", "location": "Peshawar, Pakistan",
            "hospital": "Hayatabad Medical Complex",
            "rating": 4.7, "experience_years": 16,
            "languages": ["Urdu", "English", "Pashto"],
            "insurance_accepted": ["State Life", "EFU Health"],
            "available_slots": 5, "consultation_fee": 1500,
            "education": "MBBS (KMU), FCPS Medicine",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_024", "name": "Dr. Saeed Hamid",
            "specialty": "Infectious Disease",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Services Hospital Lahore",
            "rating": 4.6, "experience_years": 14,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 6, "consultation_fee": 2000,
            "education": "MBBS, FCPS Infectious Disease",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_025", "name": "Dr. Nusrat Hussain",
            "specialty": "Infectious Disease",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Federal Government Polyclinic",
            "rating": 4.5, "experience_years": 12,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life"],
            "available_slots": 7, "consultation_fee": 1500,
            "education": "MBBS (NUMS), FCPS Medicine",
            "certifications": ["FCPS"], "telemedicine": False,
        },

        # ────────────────── DERMATOLOGY ──────────────────────────────────────
        {
            "id": "doc_026", "name": "Dr. Kiran Altaf",
            "specialty": "Dermatology", "sub_specialty": "Cosmetic Dermatology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Skin Care Institute Lahore",
            "rating": 4.8, "experience_years": 15,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["Jubilee Health", "State Life"],
            "available_slots": 5, "consultation_fee": 2500,
            "education": "MBBS, FCPS Dermatology",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_027", "name": "Dr. Arfan ul Bari",
            "specialty": "Dermatology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Pakistan Institute of Skin and Laser",
            "rating": 4.9, "experience_years": 20,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "EFU Health"],
            "available_slots": 3, "consultation_fee": 4000,
            "education": "MBBS, FCPS Dermatology, Fellowship (Germany)",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_028", "name": "Dr. Nadia Rashid",
            "specialty": "Dermatology",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Dow University of Health Sciences Hospital",
            "rating": 4.7, "experience_years": 13,
            "languages": ["Urdu", "English", "Sindhi"],
            "insurance_accepted": ["State Life", "EFU Health"],
            "available_slots": 6, "consultation_fee": 2000,
            "education": "MBBS, FCPS Dermatology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_029", "name": "Dr. Farhan Saeed",
            "specialty": "Dermatology",
            "city": "Rawalpindi", "location": "Rawalpindi, Pakistan",
            "hospital": "Benazir Bhutto Hospital",
            "rating": 4.5, "experience_years": 11,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life"],
            "available_slots": 7, "consultation_fee": 1500,
            "education": "MBBS, FCPS Dermatology",
            "certifications": ["FCPS"], "telemedicine": True,
        },

        # ────────────────── ORTHOPEDICS ──────────────────────────────────────
        {
            "id": "doc_030", "name": "Dr. Haroon Rashid",
            "specialty": "Orthopedics", "sub_specialty": "Joint Replacement",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Lahore General Hospital",
            "rating": 4.8, "experience_years": 21,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 4, "consultation_fee": 3000,
            "education": "MBBS, FRCS (UK), FCPS Orthopedics",
            "certifications": ["FCPS", "FRCS"], "telemedicine": False,
        },
        {
            "id": "doc_031", "name": "Dr. Kamran Afzal",
            "specialty": "Orthopedics",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "National Institute of Orthopedics & Rehabilitation",
            "rating": 4.7, "experience_years": 18,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "EFU Health"],
            "available_slots": 5, "consultation_fee": 3500,
            "education": "MBBS, FCPS Orthopedics",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_032", "name": "Dr. Osama Bin Khalid",
            "specialty": "Orthopedics",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Shifa International Hospital",
            "rating": 4.6, "experience_years": 14,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "Jubilee Health", "EFU Health"],
            "available_slots": 6, "consultation_fee": 4000,
            "education": "MBBS, FCPS Orthopedics",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_033", "name": "Dr. Rao Awais",
            "specialty": "Orthopedics",
            "city": "Multan", "location": "Multan, Pakistan",
            "hospital": "Nishtar Medical University Hospital",
            "rating": 4.5, "experience_years": 12,
            "languages": ["Urdu", "English", "Punjabi", "Saraiki"],
            "insurance_accepted": ["State Life"],
            "available_slots": 8, "consultation_fee": 1500,
            "education": "MBBS, FCPS Orthopedics",
            "certifications": ["FCPS"], "telemedicine": False,
        },

        # ────────────────── PSYCHIATRY ───────────────────────────────────────
        {
            "id": "doc_034", "name": "Dr. Murad Moosa Khan",
            "specialty": "Psychiatry", "sub_specialty": "Addiction Psychiatry",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Aga Khan University Hospital",
            "rating": 4.9, "experience_years": 22,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "Allianz EFU"],
            "available_slots": 3, "consultation_fee": 5000,
            "education": "MBBS, MRCPsych (UK), PhD",
            "certifications": ["MRCPsych"], "telemedicine": True,
        },
        {
            "id": "doc_035", "name": "Dr. Haider Ali Shah",
            "specialty": "Psychiatry",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Mayo Hospital Lahore",
            "rating": 4.7, "experience_years": 16,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 5, "consultation_fee": 2500,
            "education": "MBBS, FCPS Psychiatry",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_036", "name": "Dr. Irum Sohail",
            "specialty": "Psychiatry",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Institute of Psychiatry, PIMS",
            "rating": 4.8, "experience_years": 18,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "EFU Health"],
            "available_slots": 4, "consultation_fee": 3000,
            "education": "MBBS, FCPS Psychiatry",
            "certifications": ["FCPS", "MRCPsych"], "telemedicine": True,
        },
        {
            "id": "doc_037", "name": "Dr. Raza ur Rahman",
            "specialty": "Psychiatry",
            "city": "Peshawar", "location": "Peshawar, Pakistan",
            "hospital": "Lady Reading Hospital",
            "rating": 4.5, "experience_years": 13,
            "languages": ["Urdu", "English", "Pashto"],
            "insurance_accepted": ["State Life"],
            "available_slots": 7, "consultation_fee": 1500,
            "education": "MBBS, FCPS Psychiatry",
            "certifications": ["FCPS"], "telemedicine": True,
        },

        # ────────────────── PEDIATRICS ───────────────────────────────────────
        {
            "id": "doc_038", "name": "Dr. Anita Zaidi",
            "specialty": "Pediatrics", "sub_specialty": "Pediatric Infectious Disease",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Aga Khan University Hospital",
            "rating": 5.0, "experience_years": 30,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "Allianz EFU", "Adamjee"],
            "available_slots": 2, "consultation_fee": 6000,
            "education": "MBBS, FAAP (USA), PhD",
            "certifications": ["FAAP", "FPID"], "telemedicine": True,
        },
        {
            "id": "doc_039", "name": "Dr. Sajid Maqsood",
            "specialty": "Pediatrics",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Children's Hospital & ICH Lahore",
            "rating": 4.8, "experience_years": 19,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health", "EFU Health"],
            "available_slots": 5, "consultation_fee": 2000,
            "education": "MBBS, FCPS Pediatrics",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_040", "name": "Dr. Zulfiqar Ahmed Bhutta",
            "specialty": "Pediatrics", "sub_specialty": "Global Child Health",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Centre of Excellence in Women & Child Health, AKU",
            "rating": 5.0, "experience_years": 35,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "Allianz EFU"],
            "available_slots": 1, "consultation_fee": 8000,
            "education": "MBBS, FRCPCH, DCH, FRCP, FAAP, PhD",
            "certifications": ["FRCPCH", "FAAP", "FRCP"], "telemedicine": True,
        },
        {
            "id": "doc_041", "name": "Dr. Tariq Mahmood",
            "specialty": "Pediatrics",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Children's Hospital PIMS",
            "rating": 4.7, "experience_years": 16,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 6, "consultation_fee": 2500,
            "education": "MBBS, FCPS Pediatrics",
            "certifications": ["FCPS"], "telemedicine": False,
        },

        # ────────────────── NEPHROLOGY ───────────────────────────────────────
        {
            "id": "doc_042", "name": "Dr. Manzoor Hussain",
            "specialty": "Nephrology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Sindh Institute of Urology & Transplantation (SIUT) — Lahore branch",
            "rating": 4.8, "experience_years": 20,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 4, "consultation_fee": 3000,
            "education": "MBBS, FCPS Nephrology, Fellowship (USA)",
            "certifications": ["FCPS", "FASN"], "telemedicine": True,
        },
        {
            "id": "doc_043", "name": "Dr. Tahir Aziz",
            "specialty": "Nephrology",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Sindh Institute of Urology & Transplantation (SIUT)",
            "rating": 4.9, "experience_years": 23,
            "languages": ["Urdu", "English", "Sindhi"],
            "insurance_accepted": ["Jubilee Health", "EFU Health"],
            "available_slots": 3, "consultation_fee": 3500,
            "education": "MBBS, FCPS Nephrology",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_044", "name": "Dr. Parveen Akhtar",
            "specialty": "Nephrology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Shifa International Hospital",
            "rating": 4.7, "experience_years": 17,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "Jubilee Health", "EFU Health"],
            "available_slots": 5, "consultation_fee": 4000,
            "education": "MBBS, FCPS Nephrology",
            "certifications": ["FCPS"], "telemedicine": True,
        },

        # ────────────────── HEPATOLOGY ───────────────────────────────────────
        {
            "id": "doc_045", "name": "Dr. Saeed Hamid",
            "specialty": "Hepatology", "sub_specialty": "Liver Transplant",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Aga Khan University Hospital",
            "rating": 4.9, "experience_years": 24,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "Allianz EFU"],
            "available_slots": 2, "consultation_fee": 5000,
            "education": "MBBS, FRCP (UK), FACG",
            "certifications": ["FRCP", "FACG"], "telemedicine": True,
        },
        {
            "id": "doc_046", "name": "Dr. Muhammad Ali Tasneem",
            "specialty": "Hepatology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Services Institute of Medical Sciences",
            "rating": 4.7, "experience_years": 15,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 5, "consultation_fee": 2500,
            "education": "MBBS, FCPS Gastroenterology/Hepatology",
            "certifications": ["FCPS"], "telemedicine": True,
        },

        # ────────────────── UROLOGY ──────────────────────────────────────────
        {
            "id": "doc_047", "name": "Dr. Anwar ul Haq",
            "specialty": "Urology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Lahore General Hospital",
            "rating": 4.7, "experience_years": 18,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 5, "consultation_fee": 2500,
            "education": "MBBS, FCPS Urology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_048", "name": "Dr. Akhter Rashid",
            "specialty": "Urology",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "SIUT Karachi",
            "rating": 4.9, "experience_years": 25,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "EFU Health"],
            "available_slots": 3, "consultation_fee": 4000,
            "education": "MBBS, FCPS Urology, FRCS (UK)",
            "certifications": ["FCPS", "FRCS"], "telemedicine": True,
        },
        {
            "id": "doc_049", "name": "Dr. Naeem Ahmed",
            "specialty": "Urology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "PIMS Hospital",
            "rating": 4.6, "experience_years": 14,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life"],
            "available_slots": 6, "consultation_fee": 2000,
            "education": "MBBS, FCPS Urology",
            "certifications": ["FCPS"], "telemedicine": False,
        },

        # ────────────────── OPHTHALMOLOGY ────────────────────────────────────
        {
            "id": "doc_050", "name": "Dr. Khabir Ahmad",
            "specialty": "Ophthalmology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Mayo Hospital Lahore — Eye Department",
            "rating": 4.7, "experience_years": 17,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 6, "consultation_fee": 2000,
            "education": "MBBS, FCPS Ophthalmology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_051", "name": "Dr. Zeeshan Kamil",
            "specialty": "Ophthalmology",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Al-Ibrahim Eye Hospital",
            "rating": 4.8, "experience_years": 16,
            "languages": ["Urdu", "English", "Sindhi"],
            "insurance_accepted": ["Jubilee Health", "EFU Health"],
            "available_slots": 5, "consultation_fee": 2500,
            "education": "MBBS, FCPS Ophthalmology",
            "certifications": ["FCPS"], "telemedicine": True,
        },

        # ────────────────── RHEUMATOLOGY ─────────────────────────────────────
        {
            "id": "doc_052", "name": "Dr. Abid Waheed Sheikh",
            "specialty": "Rheumatology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Shaukat Khanum Memorial Cancer Hospital",
            "rating": 4.8, "experience_years": 18,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 4, "consultation_fee": 3000,
            "education": "MBBS, FCPS Rheumatology",
            "certifications": ["FCPS", "MRCP"], "telemedicine": True,
        },
        {
            "id": "doc_053", "name": "Dr. Riffat Mehboob",
            "specialty": "Rheumatology",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Liaquat National Hospital",
            "rating": 4.7, "experience_years": 15,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "EFU Health"],
            "available_slots": 5, "consultation_fee": 3500,
            "education": "MBBS, FCPS Rheumatology",
            "certifications": ["FCPS"], "telemedicine": True,
        },

        # ────────────────── HEMATOLOGY ───────────────────────────────────────
        {
            "id": "doc_054", "name": "Dr. Tahir Shamsi",
            "specialty": "Hematology",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "National Institute of Blood Diseases & Bone Marrow Transplantation",
            "rating": 4.9, "experience_years": 26,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "Allianz EFU"],
            "available_slots": 2, "consultation_fee": 4000,
            "education": "MBBS, FCPS Hematology, FRCP (UK)",
            "certifications": ["FCPS", "FRCP"], "telemedicine": True,
        },
        {
            "id": "doc_055", "name": "Dr. Kamran Mirza",
            "specialty": "Hematology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Children's Hospital Lahore",
            "rating": 4.7, "experience_years": 15,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 5, "consultation_fee": 2500,
            "education": "MBBS, FCPS Hematology",
            "certifications": ["FCPS"], "telemedicine": True,
        },

        # ────────────────── GENERAL PRACTICE ────────────────────────────────
        {
            "id": "doc_056", "name": "Dr. Ali Hassan",
            "specialty": "General Practice",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Islamabad Medical & Surgical Hospital",
            "rating": 4.6, "experience_years": 10,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "Jubilee Health", "EFU Health"],
            "available_slots": 10, "consultation_fee": 1000,
            "education": "MBBS (NUMS)",
            "certifications": [], "telemedicine": True,
        },
        {
            "id": "doc_057", "name": "Dr. Sobia Niaz",
            "specialty": "General Practice",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Indus Hospital Karachi",
            "rating": 4.5, "experience_years": 8,
            "languages": ["Urdu", "English", "Sindhi"],
            "insurance_accepted": ["State Life", "EFU Health"],
            "available_slots": 12, "consultation_fee": 800,
            "education": "MBBS (DUHS)",
            "certifications": [], "telemedicine": True,
        },
        {
            "id": "doc_058", "name": "Dr. Farrukh Ijaz",
            "specialty": "General Practice",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Lahore Medical & Dental College Hospital",
            "rating": 4.4, "experience_years": 9,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life"],
            "available_slots": 15, "consultation_fee": 700,
            "education": "MBBS (LMDC)",
            "certifications": [], "telemedicine": True,
        },
        {
            "id": "doc_059", "name": "Dr. Hina Siddiqui",
            "specialty": "General Practice",
            "city": "Rawalpindi", "location": "Rawalpindi, Pakistan",
            "hospital": "District Headquarter Hospital Rawalpindi",
            "rating": 4.3, "experience_years": 7,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life"],
            "available_slots": 14, "consultation_fee": 600,
            "education": "MBBS (RMU)",
            "certifications": [], "telemedicine": True,
        },
        {
            "id": "doc_060", "name": "Dr. Asad Raza",
            "specialty": "General Practice",
            "city": "Quetta", "location": "Quetta, Pakistan",
            "hospital": "Bolan Medical Complex",
            "rating": 4.4, "experience_years": 10,
            "languages": ["Urdu", "English", "Balochi", "Pashto"],
            "insurance_accepted": ["State Life"],
            "available_slots": 12, "consultation_fee": 600,
            "education": "MBBS (BMC)",
            "certifications": [], "telemedicine": True,
        },

        # ────────────────── ONCOLOGY ─────────────────────────────────────────
        {
            "id": "doc_061", "name": "Dr. Iftikhar Ahmed",
            "specialty": "Oncology", "sub_specialty": "Medical Oncology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Shaukat Khanum Memorial Cancer Hospital",
            "rating": 4.9, "experience_years": 22,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["Jubilee Health", "State Life"],
            "available_slots": 3, "consultation_fee": 5000,
            "education": "MBBS, FCPS Oncology, Fellowship (UK)",
            "certifications": ["FCPS", "FRCR"], "telemedicine": True,
        },
        {
            "id": "doc_062", "name": "Dr. Nida Fatima",
            "specialty": "Oncology",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Aga Khan University Hospital",
            "rating": 4.8, "experience_years": 17,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "Allianz EFU"],
            "available_slots": 4, "consultation_fee": 6000,
            "education": "MBBS, FCPS Oncology",
            "certifications": ["FCPS"], "telemedicine": True,
        },

        # ────────────────── GYNECOLOGY & OBSTETRICS ──────────────────────────
        {
            "id": "doc_063", "name": "Dr. Huma Bokhari",
            "specialty": "Gynecology",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Aga Khan University Hospital",
            "rating": 4.8, "experience_years": 20,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "Allianz EFU"],
            "available_slots": 4, "consultation_fee": 4500,
            "education": "MBBS, FCPS Gynecology, MRCOG (UK)",
            "certifications": ["FCPS", "MRCOG"], "telemedicine": True,
        },
        {
            "id": "doc_064", "name": "Dr. Nadia Waheed",
            "specialty": "Obstetrics",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Lady Aitchison Hospital",
            "rating": 4.7, "experience_years": 18,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 5, "consultation_fee": 3000,
            "education": "MBBS, FCPS Obstetrics & Gynecology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_065", "name": "Dr. Samina Qadir",
            "specialty": "Gynecology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Polyclinic Hospital PIMS",
            "rating": 4.6, "experience_years": 15,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "EFU Health"],
            "available_slots": 6, "consultation_fee": 2500,
            "education": "MBBS, FCPS Gynecology",
            "certifications": ["FCPS"], "telemedicine": True,
        },

        # ────────────────── ENT / OTOLARYNGOLOGY ─────────────────────────────
        {
            "id": "doc_066", "name": "Dr. Shabbir Ahmed",
            "specialty": "Otolaryngology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Services Hospital Lahore",
            "rating": 4.7, "experience_years": 16,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 6, "consultation_fee": 2000,
            "education": "MBBS, FCPS ENT",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_067", "name": "Dr. Tariq Mehmood",
            "specialty": "Otolaryngology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Shifa International Hospital",
            "rating": 4.6, "experience_years": 14,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "Jubilee Health", "EFU Health"],
            "available_slots": 7, "consultation_fee": 3000,
            "education": "MBBS, FCPS ENT",
            "certifications": ["FCPS"], "telemedicine": True,
        },

        # ────────────────── IMMUNOLOGY / ALLERGY ─────────────────────────────
        {
            "id": "doc_068", "name": "Dr. Lena Khalid",
            "specialty": "Immunology",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Aga Khan University Hospital",
            "rating": 4.8, "experience_years": 15,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "Allianz EFU"],
            "available_slots": 5, "consultation_fee": 4000,
            "education": "MBBS, FCPS Immunology",
            "certifications": ["FCPS"], "telemedicine": True,
        },

        # ────────────────── EMERGENCY MEDICINE ──────────────────────────────
        {
            "id": "doc_069", "name": "Dr. Aamir Shahzad",
            "specialty": "Emergency Medicine",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "PIMS Emergency Department",
            "rating": 4.7, "experience_years": 14,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "All policies"],
            "available_slots": 20, "consultation_fee": 1500,
            "education": "MBBS, FCPS Emergency Medicine",
            "certifications": ["FCPS", "ATLS", "ACLS"], "telemedicine": False,
        },
        {
            "id": "doc_070", "name": "Dr. Zainab Ali",
            "specialty": "Emergency Medicine",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Aga Khan University Hospital Emergency",
            "rating": 4.8, "experience_years": 12,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "Allianz EFU", "All policies"],
            "available_slots": 20, "consultation_fee": 2000,
            "education": "MBBS, FCPS Emergency Medicine",
            "certifications": ["FCPS", "ATLS", "ACLS"], "telemedicine": False,
        },

        # ────────────────── MORE GENERAL PRACTICE — provincial cities ─────────
        {
            "id": "doc_071", "name": "Dr. Junaid Sarfraz",
            "specialty": "General Practice",
            "city": "Multan", "location": "Multan, Pakistan",
            "hospital": "Nishtar Medical University Hospital",
            "rating": 4.4, "experience_years": 9,
            "languages": ["Urdu", "English", "Saraiki", "Punjabi"],
            "insurance_accepted": ["State Life"],
            "available_slots": 12, "consultation_fee": 700,
            "education": "MBBS (NMU)",
            "certifications": [], "telemedicine": True,
        },
        {
            "id": "doc_072", "name": "Dr. Rabia Munir",
            "specialty": "General Practice",
            "city": "Faisalabad", "location": "Faisalabad, Pakistan",
            "hospital": "Allied Hospital Faisalabad",
            "rating": 4.3, "experience_years": 7,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life"],
            "available_slots": 14, "consultation_fee": 600,
            "education": "MBBS (FMU)",
            "certifications": [], "telemedicine": True,
        },
        {
            "id": "doc_073", "name": "Dr. Imran Zafar",
            "specialty": "General Practice",
            "city": "Hyderabad", "location": "Hyderabad, Pakistan",
            "hospital": "Liaquat University Hospital",
            "rating": 4.3, "experience_years": 8,
            "languages": ["Urdu", "English", "Sindhi"],
            "insurance_accepted": ["State Life"],
            "available_slots": 13, "consultation_fee": 600,
            "education": "MBBS (LUMHS)",
            "certifications": [], "telemedicine": True,
        },
        {
            "id": "doc_074", "name": "Dr. Sumaira Nawaz",
            "specialty": "General Practice",
            "city": "Sialkot", "location": "Sialkot, Pakistan",
            "hospital": "Sialkot Teaching Hospital",
            "rating": 4.2, "experience_years": 6,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life"],
            "available_slots": 15, "consultation_fee": 600,
            "education": "MBBS",
            "certifications": [], "telemedicine": True,
        },

        # ──────── ADDITIONAL SPECIALISTS — filling 75–100+ slots ─────────────
        {
            "id": "doc_075", "name": "Dr. Tariq Waseem",
            "specialty": "Cardiology",
            "city": "Multan", "location": "Multan, Pakistan",
            "hospital": "Nishtar Medical University Hospital",
            "rating": 4.6, "experience_years": 14,
            "languages": ["Urdu", "English", "Saraiki"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 6, "consultation_fee": 1800,
            "education": "MBBS, FCPS Cardiology",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_076", "name": "Dr. Nasreen Iqbal",
            "specialty": "Endocrinology",
            "city": "Faisalabad", "location": "Faisalabad, Pakistan",
            "hospital": "Allied Hospital Faisalabad",
            "rating": 4.5, "experience_years": 11,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life"],
            "available_slots": 7, "consultation_fee": 1500,
            "education": "MBBS, FCPS Endocrinology",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_077", "name": "Dr. Khalil Ahmad",
            "specialty": "Gastroenterology",
            "city": "Peshawar", "location": "Peshawar, Pakistan",
            "hospital": "Hayatabad Medical Complex",
            "rating": 4.6, "experience_years": 13,
            "languages": ["Urdu", "English", "Pashto"],
            "insurance_accepted": ["State Life", "EFU Health"],
            "available_slots": 5, "consultation_fee": 1500,
            "education": "MBBS, FCPS Gastroenterology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_078", "name": "Dr. Amina Butt",
            "specialty": "Neurology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Neurology Institute Lahore",
            "rating": 4.7, "experience_years": 14,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 5, "consultation_fee": 3000,
            "education": "MBBS, FCPS Neurology",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_079", "name": "Dr. Shahid Waheed",
            "specialty": "Pulmonology",
            "city": "Multan", "location": "Multan, Pakistan",
            "hospital": "Nishtar Medical University Hospital",
            "rating": 4.5, "experience_years": 11,
            "languages": ["Urdu", "English", "Saraiki"],
            "insurance_accepted": ["State Life"],
            "available_slots": 7, "consultation_fee": 1500,
            "education": "MBBS, FCPS Pulmonology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_080", "name": "Dr. Uzma Hanif",
            "specialty": "Dermatology",
            "city": "Faisalabad", "location": "Faisalabad, Pakistan",
            "hospital": "Allied Hospital Faisalabad",
            "rating": 4.4, "experience_years": 9,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life"],
            "available_slots": 8, "consultation_fee": 1200,
            "education": "MBBS, FCPS Dermatology",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_081", "name": "Dr. Iqbal Memon",
            "specialty": "Psychiatry",
            "city": "Hyderabad", "location": "Hyderabad, Pakistan",
            "hospital": "Liaquat University Hospital",
            "rating": 4.4, "experience_years": 10,
            "languages": ["Urdu", "English", "Sindhi"],
            "insurance_accepted": ["State Life"],
            "available_slots": 7, "consultation_fee": 1200,
            "education": "MBBS, FCPS Psychiatry",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_082", "name": "Dr. Faiza Anwer",
            "specialty": "Pediatrics",
            "city": "Rawalpindi", "location": "Rawalpindi, Pakistan",
            "hospital": "Holy Family Hospital",
            "rating": 4.6, "experience_years": 12,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 7, "consultation_fee": 1800,
            "education": "MBBS, FCPS Pediatrics",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_083", "name": "Dr. Ghulam Nabi",
            "specialty": "Nephrology",
            "city": "Quetta", "location": "Quetta, Pakistan",
            "hospital": "Sandeman Provincial Hospital",
            "rating": 4.4, "experience_years": 12,
            "languages": ["Urdu", "English", "Balochi"],
            "insurance_accepted": ["State Life"],
            "available_slots": 6, "consultation_fee": 1200,
            "education": "MBBS, FCPS Nephrology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_084", "name": "Dr. Shaheen Akhtar",
            "specialty": "Rheumatology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Maroof International Hospital",
            "rating": 4.7, "experience_years": 15,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "Jubilee Health", "EFU Health"],
            "available_slots": 5, "consultation_fee": 3500,
            "education": "MBBS, FCPS Rheumatology",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_085", "name": "Dr. Zainab Saeed",
            "specialty": "Hematology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "PIMS Hospital",
            "rating": 4.6, "experience_years": 13,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 5, "consultation_fee": 3000,
            "education": "MBBS, FCPS Hematology",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_086", "name": "Dr. Rukhsana Kausar",
            "specialty": "Gynecology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Sir Ganga Ram Hospital Lahore",
            "rating": 4.6, "experience_years": 16,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 5, "consultation_fee": 2500,
            "education": "MBBS, FCPS Gynecology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_087", "name": "Dr. Uzair Hassan",
            "specialty": "Infectious Disease",
            "city": "Quetta", "location": "Quetta, Pakistan",
            "hospital": "Bolan Medical Complex",
            "rating": 4.4, "experience_years": 10,
            "languages": ["Urdu", "English", "Balochi"],
            "insurance_accepted": ["State Life"],
            "available_slots": 8, "consultation_fee": 1000,
            "education": "MBBS, FCPS Medicine",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_088", "name": "Dr. Hira Baig",
            "specialty": "Dermatology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Maroof International Hospital",
            "rating": 4.6, "experience_years": 10,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 7, "consultation_fee": 2500,
            "education": "MBBS, FCPS Dermatology",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_089", "name": "Dr. Farhat Abbas",
            "specialty": "Cardiology",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "National Institute of Cardiovascular Diseases (NICVD)",
            "rating": 4.8, "experience_years": 16,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["Jubilee Health", "EFU Health"],
            "available_slots": 4, "consultation_fee": 3500,
            "education": "MBBS, FCPS Cardiology",
            "certifications": ["FCPS", "FACC"], "telemedicine": True,
        },
        {
            "id": "doc_090", "name": "Dr. Amjad Siraj",
            "specialty": "Neurology",
            "city": "Peshawar", "location": "Peshawar, Pakistan",
            "hospital": "Hayatabad Medical Complex",
            "rating": 4.6, "experience_years": 13,
            "languages": ["Urdu", "English", "Pashto"],
            "insurance_accepted": ["State Life", "EFU Health"],
            "available_slots": 6, "consultation_fee": 1800,
            "education": "MBBS, FCPS Neurology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_091", "name": "Dr. Yasmeen Rashid",
            "specialty": "Hepatology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Shifa International Hospital",
            "rating": 4.7, "experience_years": 15,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "Jubilee Health", "EFU Health"],
            "available_slots": 5, "consultation_fee": 4000,
            "education": "MBBS, FCPS Gastroenterology/Hepatology",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_092", "name": "Dr. Nadeem Ahmad",
            "specialty": "Orthopedics",
            "city": "Peshawar", "location": "Peshawar, Pakistan",
            "hospital": "Lady Reading Hospital",
            "rating": 4.5, "experience_years": 13,
            "languages": ["Urdu", "English", "Pashto"],
            "insurance_accepted": ["State Life"],
            "available_slots": 7, "consultation_fee": 1500,
            "education": "MBBS, FCPS Orthopedics",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_093", "name": "Dr. Sana Zehra",
            "specialty": "Obstetrics",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Jinnah Postgraduate Medical Centre",
            "rating": 4.6, "experience_years": 14,
            "languages": ["Urdu", "English", "Sindhi"],
            "insurance_accepted": ["Jubilee Health", "EFU Health"],
            "available_slots": 6, "consultation_fee": 2500,
            "education": "MBBS, FCPS Obstetrics & Gynecology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_094", "name": "Dr. Danish Siddiqui",
            "specialty": "Urology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Urology & Kidney Institute Lahore",
            "rating": 4.7, "experience_years": 14,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 5, "consultation_fee": 2500,
            "education": "MBBS, FCPS Urology",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_095", "name": "Dr. Asim Malik",
            "specialty": "Oncology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "Shifa International Hospital",
            "rating": 4.7, "experience_years": 16,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life", "Jubilee Health", "EFU Health"],
            "available_slots": 3, "consultation_fee": 5000,
            "education": "MBBS, FCPS Oncology",
            "certifications": ["FCPS", "MRCP"], "telemedicine": True,
        },
        {
            "id": "doc_096", "name": "Dr. Rahila Taj",
            "specialty": "Ophthalmology",
            "city": "Islamabad", "location": "Islamabad, Pakistan",
            "hospital": "PIMS Eye Department",
            "rating": 4.5, "experience_years": 11,
            "languages": ["Urdu", "English"],
            "insurance_accepted": ["State Life"],
            "available_slots": 8, "consultation_fee": 2000,
            "education": "MBBS, FCPS Ophthalmology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_097", "name": "Dr. Mustafa Qureshi",
            "specialty": "Immunology",
            "city": "Lahore", "location": "Lahore, Pakistan",
            "hospital": "Allergy & Asthma Institute Lahore",
            "rating": 4.6, "experience_years": 13,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life", "Jubilee Health"],
            "available_slots": 6, "consultation_fee": 2000,
            "education": "MBBS, FCPS Immunology & Allergy",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_098", "name": "Dr. Wajeeha Rauf",
            "specialty": "Pediatrics",
            "city": "Faisalabad", "location": "Faisalabad, Pakistan",
            "hospital": "Allied Hospital Faisalabad",
            "rating": 4.5, "experience_years": 10,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life"],
            "available_slots": 9, "consultation_fee": 1200,
            "education": "MBBS, FCPS Pediatrics",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_099", "name": "Dr. Adnan Malik",
            "specialty": "Cardiology",
            "city": "Peshawar", "location": "Peshawar, Pakistan",
            "hospital": "Hayatabad Medical Complex",
            "rating": 4.6, "experience_years": 13,
            "languages": ["Urdu", "English", "Pashto"],
            "insurance_accepted": ["State Life", "EFU Health"],
            "available_slots": 6, "consultation_fee": 1800,
            "education": "MBBS, FCPS Cardiology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_100", "name": "Dr. Fareeha Ismail",
            "specialty": "General Practice",
            "city": "Peshawar", "location": "Peshawar, Pakistan",
            "hospital": "Lady Reading Hospital",
            "rating": 4.3, "experience_years": 7,
            "languages": ["Urdu", "English", "Pashto"],
            "insurance_accepted": ["State Life"],
            "available_slots": 13, "consultation_fee": 600,
            "education": "MBBS (KMU)",
            "certifications": [], "telemedicine": True,
        },
        {
            "id": "doc_101", "name": "Dr. Naveed Iqbal",
            "specialty": "Pulmonology",
            "city": "Faisalabad", "location": "Faisalabad, Pakistan",
            "hospital": "Allied Hospital Faisalabad",
            "rating": 4.5, "experience_years": 11,
            "languages": ["Urdu", "English", "Punjabi"],
            "insurance_accepted": ["State Life"],
            "available_slots": 7, "consultation_fee": 1500,
            "education": "MBBS, FCPS Pulmonology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_102", "name": "Dr. Sadia Majeed",
            "specialty": "Gastroenterology",
            "city": "Multan", "location": "Multan, Pakistan",
            "hospital": "Nishtar Medical University Hospital",
            "rating": 4.4, "experience_years": 10,
            "languages": ["Urdu", "English", "Saraiki"],
            "insurance_accepted": ["State Life"],
            "available_slots": 8, "consultation_fee": 1500,
            "education": "MBBS, FCPS Gastroenterology",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_103", "name": "Dr. Faisal Khan",
            "specialty": "Nephrology",
            "city": "Peshawar", "location": "Peshawar, Pakistan",
            "hospital": "Hayatabad Medical Complex",
            "rating": 4.5, "experience_years": 12,
            "languages": ["Urdu", "English", "Pashto"],
            "insurance_accepted": ["State Life"],
            "available_slots": 6, "consultation_fee": 1800,
            "education": "MBBS, FCPS Nephrology",
            "certifications": ["FCPS"], "telemedicine": False,
        },
        {
            "id": "doc_104", "name": "Dr. Madiha Umer",
            "specialty": "Psychiatry",
            "city": "Karachi", "location": "Karachi, Pakistan",
            "hospital": "Institute of Behavioral Sciences, DOW University",
            "rating": 4.6, "experience_years": 11,
            "languages": ["Urdu", "English", "Sindhi"],
            "insurance_accepted": ["Jubilee Health", "EFU Health"],
            "available_slots": 6, "consultation_fee": 2500,
            "education": "MBBS, FCPS Psychiatry",
            "certifications": ["FCPS"], "telemedicine": True,
        },
        {
            "id": "doc_105", "name": "Dr. Arif Hussain",
            "specialty": "Orthopedics",
            "city": "Quetta", "location": "Quetta, Pakistan",
            "hospital": "Sandeman Provincial Hospital",
            "rating": 4.3, "experience_years": 11,
            "languages": ["Urdu", "English", "Balochi"],
            "insurance_accepted": ["State Life"],
            "available_slots": 9, "consultation_fee": 1200,
            "education": "MBBS, FCPS Orthopedics",
            "certifications": ["FCPS"], "telemedicine": False,
        },
    ],
}


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE CONNECTION CLASS
# ══════════════════════════════════════════════════════════════════════════════

class DatabaseConnection:
    """Mock database connection class — swap internals for asyncpg in production."""

    def __init__(self):
        self.connected = False
        self.connection = None

    async def connect(self):
        try:
            logger.info("Establishing database connection …")
            # Production: self.connection = await asyncpg.connect(**DB_CONFIG)
            self.connected = True
            logger.info("Database connection established.")
            return True
        except Exception as e:
            logger.error("Failed to connect: %s", e)
            return False

    async def disconnect(self):
        try:
            if self.connection:
                pass  # Production: await self.connection.close()
            self.connected = False
            logger.info("Database connection closed.")
        except Exception as e:
            logger.error("Error closing connection: %s", e)

    async def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        logger.info("Executing query: %s", query)
        return []

    async def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        logger.info("Fetch one: %s", query)
        return None

    async def fetch_all(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        logger.info("Fetch all: %s", query)
        return []


_db_connection = DatabaseConnection()


async def get_db_connection() -> DatabaseConnection:
    if not _db_connection.connected:
        await _db_connection.connect()
    return _db_connection


async def close_db_connection():
    await _db_connection.disconnect()


async def init_db():
    try:
        await get_db_connection()
        logger.info("Database schema initialised (mock).")
        return True
    except Exception as e:
        logger.error("DB init failed: %s", e)
        return False


# ══════════════════════════════════════════════════════════════════════════════
# QUERY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

async def get_doctor_by_id(doctor_id: str) -> Optional[Dict[str, Any]]:
    for doc in MOCK_DATABASE["doctors"]:
        if doc["id"] == doctor_id:
            return doc
    return None


async def get_doctors_by_specialty(specialty: str) -> List[Dict[str, Any]]:
    return [
        d for d in MOCK_DATABASE["doctors"]
        if d["specialty"].lower() == specialty.lower()
    ]


async def get_doctors_by_city(city: str) -> List[Dict[str, Any]]:
    return [
        d for d in MOCK_DATABASE["doctors"]
        if city.lower() in d["city"].lower()
    ]


async def get_all_doctors() -> List[Dict[str, Any]]:
    return MOCK_DATABASE["doctors"]


# ══════════════════════════════════════════════════════════════════════════════
# CORE RECOMMENDATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

# Emergency symptoms that always return Emergency Medicine
_EMERGENCY_SYMPTOMS = {
    "chest pain", "heart attack", "stroke", "unconscious",
    "breathlessness", "severe bleeding", "seizure",
    "anaphylaxis", "severe allergic reaction",
}


def _is_emergency(disease: str, symptoms: Optional[List[str]] = None) -> bool:
    d = disease.lower()
    emergency_diseases = {"heart attack", "stroke", "anaphylaxis", "severe bleeding"}
    if d in emergency_diseases:
        return True
    if symptoms:
        for s in symptoms:
            if any(e in s.lower() for e in _EMERGENCY_SYMPTOMS):
                return True
    return False


def _score_doctor(
    doc: Dict[str, Any],
    preferred_city: Optional[str],
    urgency: str,
) -> float:
    """
    Composite score for sorting:
      - Rating (heavily weighted)
      - City match bonus
      - Available slots bonus
      - Telemedicine bonus for urgent cases
      - Experience bonus
    """
    score  = doc["rating"] * 20                        # 0–100 base
    score += doc["experience_years"] * 0.5             # experience
    score += min(doc["available_slots"], 10) * 0.3     # availability

    if preferred_city and doc["city"].lower() == preferred_city.lower():
        score += 15                                     # same city

    if urgency in ("urgent", "emergency") and doc.get("telemedicine"):
        score += 5

    return score


async def recommend_doctors(
    disease:         str,
    symptoms:        Optional[List[str]] = None,
    preferred_city:  Optional[str]       = None,
    top_k:           int                 = 5,
) -> Dict[str, Any]:
    """
    Primary recommendation function called by recommendation_agent.py.

    Parameters
    ----------
    disease        : disease name from the Medical Reasoning Agent
    symptoms       : raw symptom list (for emergency detection)
    preferred_city : patient's city for proximity ranking
    top_k          : max doctors to return

    Returns
    -------
    {
        "disease": str,
        "primary_specialty": str,
        "alternative_specialties": [str],
        "urgency": "normal" | "urgent" | "emergency",
        "advice": str,
        "recommended_doctors": [Dict]
    }
    """
    mapping           = get_specialty_for_disease(disease)
    primary_specialty = mapping["primary"]
    alt_specialties   = mapping.get("alternative", [])

    # Determine urgency
    if _is_emergency(disease, symptoms):
        urgency = "emergency"
    elif primary_specialty in ("Emergency Medicine", "Oncology", "Neurology"):
        urgency = "urgent"
    else:
        urgency = "normal"

    # Emergency → always add Emergency Medicine first
    if urgency == "emergency":
        primary_specialty = "Emergency Medicine"
        alt_specialties   = mapping.get("alternative", []) + ["Emergency Medicine"]

    all_docs: List[Dict] = list(MOCK_DATABASE["doctors"])

    # Pool: primary specialty docs first, then alternative
    primary_pool = [d for d in all_docs if d["specialty"] == primary_specialty]
    alt_pool     = [
        d for d in all_docs
        if d["specialty"] in alt_specialties and d not in primary_pool
    ]

    # Sort each pool by composite score
    primary_pool.sort(key=lambda d: _score_doctor(d, preferred_city, urgency), reverse=True)
    alt_pool.sort(    key=lambda d: _score_doctor(d, preferred_city, urgency), reverse=True)

    # Merge: prefer primary, fill remaining from alt if needed
    merged = primary_pool[:top_k]
    if len(merged) < top_k:
        merged += alt_pool[: top_k - len(merged)]

    # Trim to top_k and annotate with match_reason
    result_docs = []
    for doc in merged[:top_k]:
        annotated = dict(doc)
        if doc["specialty"] == primary_specialty:
            annotated["match_reason"] = f"Primary specialist for {disease}"
        else:
            annotated["match_reason"] = f"Alternative specialist ({doc['specialty']})"
        result_docs.append(annotated)

    # Build advice string
    advice_map = {
        "emergency": (
            "⚠ EMERGENCY: Please go to the nearest A&E immediately "
            "or call 1122 (Rescue Punjab) / 115 (Edhi Foundation). "
            "Do not delay seeking emergency care."
        ),
        "urgent": (
            f"Please book an appointment with a {primary_specialty} specialist "
            "within 24–48 hours. Telemedicine options are available above."
        ),
        "normal": (
            f"Book an appointment with a {primary_specialty} specialist. "
            "Consult a qualified doctor for proper medical advice."
        ),
    }

    return {
        "disease":                disease,
        "primary_specialty":      primary_specialty,
        "alternative_specialties": alt_specialties,
        "urgency":                urgency,
        "advice":                 advice_map[urgency],
        "recommended_doctors":    result_docs,
        "total_matched":          len(result_docs),
    }


# ══════════════════════════════════════════════════════════════════════════════
# APPOINTMENT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

async def create_appointment(appointment_data: Dict[str, Any]) -> Dict[str, Any]:
    appointment = {
        "id":         f"apt_{len(MOCK_DATABASE['appointments']) + 1:04d}",
        **appointment_data,
        "created_at": datetime.now().isoformat(),
        "status":     AppointmentStatus.SCHEDULED,
    }
    MOCK_DATABASE["appointments"].append(appointment)
    logger.info("Appointment created: %s", appointment["id"])
    return appointment


async def get_patient_appointments(patient_id: str) -> List[Dict[str, Any]]:
    return [
        a for a in MOCK_DATABASE["appointments"]
        if a.get("patient_id") == patient_id
    ]


async def update_doctor_availability(
    doctor_id: str,
    date: str,
    slots: List[str],
) -> bool:
    logger.info("Updating availability: doctor=%s date=%s", doctor_id, date)
    return True


# ══════════════════════════════════════════════════════════════════════════════
# STATS / DEBUG UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def db_stats() -> Dict[str, Any]:
    docs = MOCK_DATABASE["doctors"]
    by_city      = {}
    by_specialty = {}
    for d in docs:
        by_city[d["city"]]           = by_city.get(d["city"], 0) + 1
        by_specialty[d["specialty"]] = by_specialty.get(d["specialty"], 0) + 1
    return {
        "total_doctors":        len(docs),
        "total_appointments":   len(MOCK_DATABASE["appointments"]),
        "doctors_by_city":      dict(sorted(by_city.items(), key=lambda x: -x[1])),
        "doctors_by_specialty": dict(sorted(by_specialty.items(), key=lambda x: -x[1])),
    }


# ══════════════════════════════════════════════════════════════════════════════
# QUICK SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio

    async def _demo():
        stats = db_stats()
        print(f"\n{'═'*55}")
        print(f"  Total doctors   : {stats['total_doctors']}")
        print(f"  By city         : {stats['doctors_by_city']}")
        print(f"  By specialty    : {stats['doctors_by_specialty']}")
        print(f"{'═'*55}\n")

        test_cases = [
            ("Diabetes",    ["excessive thirst", "fatigue"], "Lahore"),
            ("Dengue",      ["fever", "muscle pain", "rash"], "Karachi"),
            ("Depression",  ["fatigue", "sadness"], "Islamabad"),
            ("Heart Attack",["chest pain", "breathlessness"], "Rawalpindi"),
            ("Tuberculosis",["cough", "weight loss"], "Peshawar"),
        ]

        for disease, syms, city in test_cases:
            result = await recommend_doctors(disease, syms, city, top_k=3)
            print(f"Disease   : {disease}  |  City: {city}")
            print(f"Specialty : {result['primary_specialty']}  |  Urgency: {result['urgency'].upper()}")
            for doc in result["recommended_doctors"]:
                tele = "📱" if doc.get("telemedicine") else "🏥"
                print(f"  {tele} {doc['name']:<32} {doc['city']:<14} ⭐{doc['rating']}  PKR {doc['consultation_fee']:,}")
            print(f"  ℹ  {result['advice'][:80]}…\n")

    asyncio.run(_demo())