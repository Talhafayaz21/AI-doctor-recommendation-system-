import json
import re
import logging
import numpy as np
import joblib
import os
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None
from typing import List, Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# High-risk conditions that trigger elevated risk_level regardless of probability
_HIGH_RISK_DISEASES = {
    "COVID-19", "Pneumonia", "Tuberculosis", "Heart Attack",
    "Dengue", "Malaria", "Hepatitis B", "Hepatitis C",
    "Meningitis", "Sepsis", "Encephalitis", "Severe Acute Respiratory Syndrome",
    "Middle East Respiratory Syndrome"
}

_MEDIUM_RISK_DISEASES = {
    "Influenza", "Typhoid", "Hypertension", "Diabetes",
    "Asthma", "Hepatitis A", "Cholera", "Hepatitis E"
}

class PredictionService:
    def __init__(self):
        # Set paths to the ML model files relative to the backend directory
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(backend_dir, "..", "..", "..", "ml", "saved_models", "disease_model.pkl")
        self.mlb_path = os.path.join(backend_dir, "..", "..", "..", "ml", "saved_models", "symptom_binarizer.pkl")
        self.le_path = os.path.join(backend_dir, "..", "..", "..", "ml", "saved_models", "label_encoder.pkl")
        
        self.model = self._load_model()
        self.mlb = self._load_mlb()
        self.le = self._load_label_encoder()
        
    def _load_model(self):
        """Load ML model for disease prediction"""
        try:
            if os.path.exists(self.model_path):
                model = joblib.load(self.model_path)
                logger.info(f"Loaded model from {self.model_path}")
                return model
            else:
                logger.warning(f"Model file not found at {self.model_path}. Using fallback model.")
                return self._create_fallback_model()
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}. Using fallback model.")
            return self._create_fallback_model()
    
    def _load_mlb(self):
        """Load MultiLabelBinarizer"""
        try:
            if os.path.exists(self.mlb_path):
                return joblib.load(self.mlb_path)
        except Exception as e:
            logger.warning(f"Could not load symptom binarizer: {e}")
        return None 
    
    def _load_label_encoder(self):
        """Load LabelEncoder"""
        try:
            if os.path.exists(self.le_path):
                return joblib.load(self.le_path)
        except Exception as e:
            logger.warning(f"Could not load label encoder: {e}")
        return None
        
    def _load_model(self):
        """Load ML model for disease prediction"""
        try:
            if os.path.exists(self.model_path):
                model = joblib.load(self.model_path)
                logger.info(f"Loaded model from {self.model_path}")
                return model
            else:
                logger.warning(f"Model file not found at {self.model_path}. Using fallback model.")
                return self._create_fallback_model()
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}. Using fallback model.")
            return self._create_fallback_model()
    
    def _create_fallback_model(self):
        """Create a simple fallback model for predictions"""
        # Simple rule-based model as fallback
        return None
    
    def _initialize_symptom_encoder(self):
        """Initialize symptom encoder mapping"""
        common_symptoms = [
            'fever', 'cough', 'headache', 'fatigue', 'nausea',
            'vomiting', 'diarrhea', 'chest_pain', 'shortness_of_breath',
            'dizziness', 'sore_throat', 'runny_nose', 'body_ache',
            'rash', 'joint_pain', 'abdominal_pain', 'back_pain',
            'muscle_weakness', 'weight_loss', 'night_sweats'
        ]
        return {symptom: idx for idx, symptom in enumerate(common_symptoms)}
    
    def _initialize_disease_labels(self):
        """Initialize disease labels"""
        return [
            'Common Cold',
            'Influenza',
            'COVID-19',
            'Pneumonia',
            'Bronchitis',
            'Strep Throat',
            'Migraine',
            'Tension Headache',
            'Gastroenteritis',
            'Food Poisoning',
            'Allergic Reaction',
            'Anxiety',
            'Depression',
            'Hypertension',
            'Diabetes',
            'Asthma',
            'Allergy',
            'Sinusitis',
            'Ear Infection',
            'Urinary Tract Infection'
        ]
    
    async def predict_diseases(self, symptoms: List[str], age: int, 
                                gender: str, medical_history: List[str] = None) -> Dict[str, Any]:
        """Predict possible diseases based on symptoms and patient info"""
        try:
            # Use ML model if available (uses proper symptom ML encoding)
            if self.model is not None and self.mlb is not None and self.le is not None:
                try:
                    # Normalise symptoms to match training data encoding
                    normalised = [self._normalise_symptom(s) for s in symptoms]
                    known_symptoms = [s for s in normalised if s in self.mlb.classes_]
                    unknown = [s for s in normalised if s not in self.mlb.classes_]
                    
                    if not known_symptoms:
                        return await self._fallback_prediction(symptoms, age, gender, medical_history)
                    
                    # Encode symptoms using the fitted MultiLabelBinarizer
                    X = self.mlb.transform([known_symptoms])
                    probabilities = self.model.predict_proba(X)[0]
                    
                    # Get top predictions
                    top_indices = np.argsort(probabilities)[::-1][:5]
                    
                    predictions = []
                    confidence_scores = []
                    
                    for idx in top_indices:
                        if probabilities[idx] > 0.01:
                            predictions.append({
                                'disease': self.le.classes_[idx],
                                'probability': round(float(probabilities[idx]), 4),
                                'confidence': round(float(probabilities[idx]), 4)
                            })
                            confidence_scores.append(round(float(probabilities[idx]), 4))
                    
                    # Compute risk level
                    risk_level = self._compute_risk(predictions)
                    
                    return {
                        'predictions': predictions,
                        'conditions': [
                            {
                                'name': pred['disease'],
                                'confidence': pred['probability'],
                                'category': self._get_disease_category(pred['disease'])
                            }
                            for pred in predictions
                        ],
                        'confidence_scores': confidence_scores,
                        'risk_level': risk_level,
                        'model_used': 'ML_model',
                        'timestamp': datetime.now().isoformat()
                    }
                    
                except Exception as e:
                    logger.error(f"Error in ML prediction: {str(e)}")
                    return await self._fallback_prediction(symptoms, age, gender, medical_history)
            else:
                # Use fallback prediction
                return await self._fallback_prediction(symptoms, age, gender, medical_history)
                
        except Exception as e:
            logger.error(f"Error in disease prediction: {str(e)}")
            return await self._fallback_prediction(symptoms, age, gender, medical_history)
    
    def _normalise_symptom(self, raw: str) -> str:
        """Normalise a symptom string to match training data encoding."""
        s = str(raw).lower().strip()
        s = re.sub(r"\s+", "_", s)
        s = re.sub(r"[^a-z0-9_]", "", s)
        return s
    
    async def _fallback_prediction(self, symptoms: List[str], age: int, 
                                    gender: str, medical_history: List[str] = None) -> Dict[str, Any]:
        """Rule-based fallback prediction"""
        symptom_text = " ".join(symptoms).lower()
        
        # Define symptom-disease mappings
        disease_patterns = {
            'Common Cold': ['cough', 'runny_nose', 'sore_throat', 'sneezing'],
            'Influenza': ['fever', 'body_ache', 'fatigue', 'headache', 'cough'],
            'COVID-19': ['fever', 'cough', 'shortness_of_breath', 'fatigue', 'loss_of_taste'],
            'Pneumonia': ['cough', 'fever', 'shortness_of_breath', 'chest_pain'],
            'Bronchitis': ['cough', 'chest_pain', 'shortness_of_breath', 'fatigue'],
            'Strep Throat': ['sore_throat', 'fever', 'headache', 'nausea'],
            'Migraine': ['headache', 'nausea', 'sensitivity_to_light'],
            'Gastroenteritis': ['nausea', 'vomiting', 'diarrhea', 'abdominal_pain'],
            'Food Poisoning': ['nausea', 'vomiting', 'diarrhea', 'abdominal_pain'],
            'Allergic Reaction': ['rash', 'runny_nose', 'sneezing'],
            'Anxiety': ['nervousness', 'panic', 'restlessness'],
            'Asthma': ['shortness_of_breath', 'wheezing', 'cough'],
            'Sinusitis': ['headache', 'facial_pain', 'runny_nose'],
        }
        
        predictions = []
        confidence_scores = []
        
        for disease, patterns in disease_patterns.items():
            matches = sum(1 for pattern in patterns if pattern in symptom_text)
            if matches > 0:
                confidence = min(matches / len(patterns), 1.0)
                predictions.append({
                    'disease': disease,
                    'probability': confidence * 0.7,  # Scale down for fallback
                    'confidence': confidence * 0.7
                })
                confidence_scores.append(confidence * 0.7)
        
        # Sort by confidence
        predictions.sort(key=lambda x: x['confidence'], reverse=True)
        predictions = predictions[:5]  # Top 5
        confidence_scores = sorted(confidence_scores, reverse=True)[:5]
        
        return {
            'predictions': predictions,
            'conditions': [
                {
                    'name': pred['disease'],
                    'confidence': pred['probability'],
                    'category': self._get_disease_category(pred['disease'])
                }
                for pred in predictions
            ],
            'confidence_scores': confidence_scores,
            'model_used': 'fallback_rules',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_disease_category(self, disease_name: str) -> str:
        """Get disease category"""
        categories = {
            'Common Cold': 'Respiratory',
            'Influenza': 'Respiratory',
            'COVID-19': 'Respiratory',
            'Pneumonia': 'Respiratory',
            'Bronchitis': 'Respiratory',
            'Strep Throat': 'Respiratory',
            'Migraine': 'Neurological',
            'Tension Headache': 'Neurological',
            'Gastroenteritis': 'Gastrointestinal',
            'Food Poisoning': 'Gastrointestinal',
            'Allergic Reaction': 'Allergy',
            'Anxiety': 'Mental Health',
            'Depression': 'Mental Health',
            'Hypertension': 'Cardiovascular',
            'Diabetes': 'Metabolic',
            'Asthma': 'Respiratory',
            'Allergy': 'Allergy',
            'Sinusitis': 'Respiratory',
            'Ear Infection': 'ENT',
            'Urinary Tract Infection': 'Genitourinary'
        }
        return categories.get(disease_name, 'General')
    
    def _compute_risk(self, predictions: List[Dict]) -> str:
        """Compute risk level from predictions."""
        if not predictions:
            return "low"
        
        top_disease = predictions[0]["disease"]
        top_prob = predictions[0]["probability"]
        
        if top_disease in _HIGH_RISK_DISEASES and top_prob >= 0.20:
            return "high"
        if top_disease in _MEDIUM_RISK_DISEASES and top_prob >= 0.30:
            return "medium"
        if top_prob >= 0.65:
            return "medium"
        
        return "low"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        if self.mlb is not None:
            n_features = len(self.mlb.classes_)
        else:
            n_features = 0
        if self.le is not None:
            n_diseases = len(self.le.classes_)
            disease_list = list(self.le.classes_)
        else:
            n_diseases = 0
            disease_list = []
        
        return {
            'model_path': self.model_path,
            'model_loaded': self.model is not None,
            'n_features': n_features,
            'n_diseases': n_diseases,
            'disease_list': disease_list,
            'timestamp': datetime.now().isoformat()
        }

# Global instance
prediction_service = PredictionService()

# Module-level wrapper functions for backward compatibility
async def predict_diseases(symptoms: List[str], age: int, gender: str, medical_history: List[str] = None) -> Dict[str, Any]:
    """Module-level wrapper for disease prediction."""
    return await prediction_service.predict_diseases(symptoms, age, gender, medical_history)

def get_model_info() -> Dict[str, Any]:
    """Module-level wrapper for model info."""
    return prediction_service.get_model_info()