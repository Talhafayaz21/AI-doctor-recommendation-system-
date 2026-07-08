from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
from app.services.orchestrator import process_medical_query
from app.database.db import get_db_connection
from app.agents.diagnosis_agent import get_condition_info

router = APIRouter()

class DiagnosisRequest(BaseModel):
    symptoms: List[str]
    patient_age: int
    patient_gender: str
    medical_history: Optional[List[str]] = None
    duration: Optional[str] = None

class DiagnosisResponse(BaseModel):
    possible_conditions: List[dict]
    confidence_scores: List[float]
    recommendations: List[str]
    urgency_level: str
    timestamp: str

@router.post("/assess", response_model=DiagnosisResponse)
async def assess_diagnosis(request: DiagnosisRequest):
    """Assess potential diagnoses based on symptoms"""
    try:
        # Create a simulated user input from symptoms for the orchestrator
        user_input = f"I have the following symptoms: {', '.join(request.symptoms)}. " \
                    f"I am {request.patient_age} years old, {request.patient_gender}."

        # Use the orchestrator for full pipeline processing
        orchestrator_result = await process_medical_query(
            user_input=user_input,
            patient_age=request.patient_age,
            patient_gender=request.patient_gender,
            medical_history=request.medical_history
        )

        # Extract diagnosis results from orchestrator
        diagnosis_data = orchestrator_result.get("diagnosis", {})
        ml_prediction = orchestrator_result.get("ml_prediction", {})

        # Debug logging
        logging.info(f"Orchestrator result keys: {list(orchestrator_result.keys())}")
        logging.info(f"Diagnosis data: {diagnosis_data}")
        logging.info(f"ML prediction: {ml_prediction}")

        # For now, return diagnosis conditions directly to test
        conditions = diagnosis_data.get("conditions", [])
        formatted_conditions = []
        for cond in conditions:
            formatted_conditions.append({
                "name": cond.get("name", ""),
                "confidence": cond.get("confidence", 0.5),
                "category": cond.get("specialist", "General")
            })

        # Determine urgency level
        urgency = diagnosis_data.get("urgency", "low")

        return DiagnosisResponse(
            possible_conditions=formatted_conditions,
            confidence_scores=[],
            recommendations=diagnosis_data.get("follow_up_questions", []),
            urgency_level=urgency,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logging.error(f"Error in diagnosis assessment: {str(e)}")
        raise

@router.post("/predict")
async def predict_conditions(request: DiagnosisRequest):
    """Predict possible conditions using ML model"""
    try:
        predictions = await prediction_service.predict_diseases(
            symptoms=request.symptoms,
            age=request.patient_age,
            gender=request.patient_gender,
            medical_history=request.medical_history
        )
        return predictions
    except Exception as e:
        logging.error(f"Error in prediction: {str(e)}")
        raise

@router.get("/conditions/{condition_id}")
async def get_condition_details(condition_id: str):
    """Get detailed information about a medical condition"""
    try:
        condition = await get_condition_info(condition_id)
        if not condition:
            raise HTTPException(status_code=404, detail="Condition not found")
        return condition
    except Exception as e:
        logging.error(f"Error retrieving condition details: {str(e)}")
        raise

@router.get("/urgency-calculator")
async def calculate_urgency(symptoms: List[str]):
    """Calculate urgency level based on symptoms"""
    try:
        urgency_level = await _determine_urgency_from_symptoms(symptoms)
        return {"urgency_level": urgency_level, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logging.error(f"Error calculating urgency: {str(e)}")
        raise

async def _combine_diagnosis_results(ai_result, ml_result):
    """Combine AI and ML diagnosis results"""
    combined = []
    ai_conditions = ai_result.get("conditions", [])
    ml_conditions = ml_result.get("conditions", [])

    # Merge and score conditions
    condition_map = {}
    for cond in ai_conditions:
        # Convert diagnosis agent format to expected format
        condition_map[cond["name"]] = {
            "name": cond["name"],
            "confidence": cond.get("confidence", 0.5),
            "category": cond.get("specialist", "General")
        }

    for cond in ml_conditions:
        if cond["name"] in condition_map:
            condition_map[cond["name"]]["ml_confidence"] = cond.get("confidence", 0.5)
        else:
            condition_map[cond["name"]] = {
                "name": cond["name"],
                "confidence": cond.get("confidence", 0.5),
                "category": cond.get("category", "General")
            }

    return list(condition_map.values())

async def _determine_urgency(ai_diagnosis, symptoms):
    """Determine urgency level based on diagnosis and symptoms"""
    urgent_keywords = ["severe", "emergency", "critical", "urgent", "life-threatening"]
    symptoms_text = " ".join(symptoms).lower()
    
    if any(keyword in symptoms_text for keyword in urgent_keywords):
        return "high"
    elif ai_diagnosis.get("urgency") == "high":
        return "high"
    elif ai_diagnosis.get("urgency") == "medium":
        return "medium"
    else:
        return "low"

async def _determine_urgency_from_symptoms(symptoms):
    """Determine urgency from symptoms list"""
    urgent_symptoms = [
        "chest pain", "difficulty breathing", "severe bleeding",
        "loss of consciousness", "severe allergic reaction",
        "sudden confusion", "severe headache", "persistent vomiting"
    ]
    
    symptoms_lower = [s.lower() for s in symptoms]
    urgent_count = sum(1 for s in symptoms_lower if any(us in s for us in urgent_symptoms))
    
    if urgent_count > 0:
        return "high"
    elif len(symptoms) > 3:
        return "medium"
    else:
        return "low"