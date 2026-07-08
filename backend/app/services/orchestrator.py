"""
Orchestrator Service
Coordinates the workflow between symptom extraction, ML prediction, 
diagnosis, recommendation, and safety checking agents.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from app.agents.symptom_agent import analyze as extract_symptoms
from app.agents.diagnosis_agent import analyze as diagnose
from app.agents.recommendation_agent import recommend as recommend
from app.agents.safety_agent import validate as check_safety
from app.services.prediction_service import predict_diseases
from app.utils.config import settings

logger = logging.getLogger(__name__)


class OrchestratorService:
    """Main orchestrator that coordinates all agents and services."""
    
    def __init__(self):
        self.settings = settings
        logger.info("Orchestrator service initialized")
    
    async def process_medical_query(
        self, 
        user_input: str, 
        patient_age: Optional[int] = None,
        patient_gender: Optional[str] = None,
        medical_history: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process a medical query through the full pipeline:
        Symptom Extraction -> ML Prediction -> Diagnosis -> Recommendation -> Safety Check
        
        Args:
            user_input: Raw user input describing symptoms
            patient_age: Patient's age (optional)
            patient_gender: Patient's gender (optional)
            medical_history: Patient's medical history (optional)
            
        Returns:
            Dict containing results from each stage of the pipeline
        """
        try:
            logger.info(f"Processing medical query: {user_input[:100]}...")
            
            # Stage 1: Symptom Extraction
            logger.info("Stage 1: Extracting symptoms")
            symptom_result = await extract_symptoms(user_input)
            symptoms = symptom_result.get("symptoms", [])
            logger.info(f"Extracted symptoms: {symptoms}")
            
            # Stage 2: ML Prediction (if model available)
            logger.info("Stage 2: Running ML prediction")
            ml_prediction = {}
            if settings.ENABLE_DIAGNOSIS:  # This flag might be better named for ML
                try:
                    ml_prediction = await predict_diseases(
                        symptoms=symptoms,
                        age=patient_age or 30,  # Default age
                        gender=patient_gender or "other",
                        medical_history=medical_history
                    )
                    logger.info(f"ML prediction completed. Model used: {ml_prediction.get('model_used')}")
                except Exception as e:
                    logger.warning(f"ML prediction failed: {e}. Continuing with rule-based approach.")
                    ml_prediction = {"error": str(e), "model_used": "failed"}
            
            # Stage 3: Medical Reasoning/Diagnosis
            logger.info("Stage 3: Running diagnosis agent")
            symptom_data = {
                "symptoms": symptoms,
                "duration": symptom_result.get("duration", "unknown"),
                "severity": symptom_result.get("severity", "unknown"),
                "body_parts": symptom_result.get("body_parts", []),
                "patient_age": patient_age,
                "patient_gender": patient_gender
            }
            
            diagnosis_result = await diagnose(symptom_data=symptom_data)
            logger.info(f"Diagnosis completed. Risk level: {diagnosis_result.get('risk_level')}")
            
            # Stage 4: Recommendation Generation
            logger.info("Stage 4: Generating recommendations")
            recommendation_result = await recommend(
                diagnosis_data=diagnosis_result,
                symptom_data=symptom_data
            )
            logger.info(f"Recommendations generated. Specialist: {recommendation_result.get('recommended_specialist')}")
            
            # Stage 5: Safety Check
            logger.info("Stage 5: Performing safety check")
            safety_result = {}
            if settings.ENABLE_SAFETY_CHECKS:
                # Combine all results for safety validation
                combined_response = {
                    "symptoms": symptoms,
                    "diagnosis": diagnosis_result,
                    "recommendations": recommendation_result,
                    "ml_prediction": ml_prediction,
                    "pipeline_status": "completed"
                }
                safety_result = await check_safety(combined_response, user_input)
                logger.info(f"Safety check completed. Safe: {safety_result.get('safe', True)}")
            
            # Compile final result
            final_result = {
                "input": user_input,
                "symptoms": symptom_result,
                "ml_prediction": ml_prediction,
                "diagnosis": diagnosis_result,
                "recommendations": recommendation_result,
                "safety": safety_result,
                "pipeline_status": "completed",
                "timestamp": self.settings.get_timestamp()
            }
            
            logger.info("Medical query processing completed successfully")
            return final_result
            
        except Exception as e:
            logger.error(f"Error in orchestrator pipeline: {e}", exc_info=True)
            return {
                "input": user_input,
                "error": str(e),
                "pipeline_status": "failed",
                "timestamp": self.settings.get_timestamp()
            }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get the health status of all components in the orchestrator."""
        try:
            # Test each component briefly
            status = {
                "orchestrator": "healthy",
                "timestamp": self.settings.get_timestamp(),
                "components": {}
            }
            
            # Test symptom agent (lightweight)
            try:
                test_result = await extract_symptoms("headache")
                status["components"]["symptom_agent"] = "healthy" if test_result else "degraded"
            except Exception as e:
                status["components"]["symptom_agent"] = f"unhealthy: {str(e)}"
            
            # Test prediction service
            try:
                from app.services.prediction_service import get_model_info
                model_info = get_model_info()
                status["components"]["prediction_service"] = "healthy" if model_info.get("model_loaded") else "degraded (fallback)"
            except Exception as e:
                status["components"]["prediction_service"] = f"unhealthy: {str(e)}"
            
            # Test diagnosis agent (will use fallback if OpenAI fails)
            try:
                test_diagnosis = await diagnose({"symptoms": ["fever"], "duration": "1 day", "severity": "low"})
                status["components"]["diagnosis_agent"] = "healthy" if test_diagnosis else "degraded"
            except Exception as e:
                status["components"]["diagnosis_agent"] = f"unhealthy: {str(e)}"
            
            # Test recommendation agent
            try:
                test_recommendation = await recommend(
                    {"conditions": [{"name": "Common Cold", "probability": "moderate"}], "risk_level": "low"},
                    {"symptoms": ["fever"], "duration": "1 day", "severity": "low"}
                )
                status["components"]["recommendation_agent"] = "healthy" if test_recommendation else "degraded"
            except Exception as e:
                status["components"]["recommendation_agent"] = f"unhealthy: {str(e)}"
            
            # Test safety agent
            try:
                test_safety = await check_safety({"user_input": "test", "symptoms": ["fever"]}, "test")
                status["components"]["safety_agent"] = "healthy" if test_safety else "degraded"
            except Exception as e:
                status["components"]["safety_agent"] = f"unhealthy: {str(e)}"
            
            # Overall status
            unhealthy_components = [k for k, v in status["components"].items() if "unhealthy" in str(v)]
            if unhealthy_components:
                status["orchestrator"] = f"degraded - issues with: {', '.join(unhealthy_components)}"
            else:
                status["orchestrator"] = "healthy"
                
            return status
            
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {
                "orchestrator": "unhealthy",
                "error": str(e),
                "timestamp": self.settings.get_timestamp()
            }


# Global instance
orchestrator_service = OrchestratorService()

# Module-level wrapper functions
async def process_medical_query(
    user_input: str,
    patient_age: Optional[int] = None,
    patient_gender: Optional[str] = None,
    medical_history: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Module-level wrapper for processing medical queries."""
    return await orchestrator_service.process_medical_query(
        user_input, patient_age, patient_gender, medical_history
    )

async def get_orchestrator_health() -> Dict[str, Any]:
    """Module-level wrapper for getting orchestrator health status."""
    return await orchestrator_service.get_health_status()