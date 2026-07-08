from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecommendationService:
    """Service for generating health and lifestyle recommendations"""
    
    def __init__(self):
        self.recommendation_db = self._initialize_recommendations()
        
    def _initialize_recommendations(self) -> Dict[str, Any]:
        """Initialize recommendation database"""
        return {
            'symptoms': {
                'fever': {
                    'immediate': ['Rest and stay hydrated', 'Monitor temperature regularly'],
                    'lifestyle': ['Get plenty of sleep', 'Drink warm fluids'],
                    'warnings': ['Seek medical attention if temperature exceeds 103°F', 
                                 'Contact doctor if fever persists more than 3 days']
                },
                'cough': {
                    'immediate': ['Stay hydrated', 'Use honey and warm tea', 'Avoid irritants'],
                    'lifestyle': ['Use humidifier', 'Practice breathing exercises'],
                    'warnings': ['See doctor if cough persists more than 3 weeks',
                                 'Seek immediate care if coughing blood']
                },
                'headache': {
                    'immediate': ['Rest in dark, quiet room', 'Apply cold compress', 'Hydrate'],
                    'lifestyle': ['Practice stress management', 'Maintain regular sleep schedule'],
                    'warnings': ['Seek immediate care for severe, sudden headaches',
                                 'Contact doctor if headaches worsen or change pattern']
                },
                'fatigue': {
                    'immediate': ['Rest when needed', 'Prioritize sleep'],
                    'lifestyle': ['Regular exercise', 'Balanced diet', 'Stress reduction'],
                    'warnings': ['Consult doctor if fatigue persists despite adequate rest',
                                 'Seek care if accompanied by other concerning symptoms']
                }
            },
            'conditions': {
                'respiratory': {
                    'lifestyle': ['Quit smoking', 'Avoid air pollution', 'Practice breathing exercises'],
                    'diet': ['Anti-inflammatory foods', 'Omega-3 rich foods', 'Plenty of fluids'],
                    'exercise': ['Cardio exercises', 'Breathing exercises', 'Yoga']
                },
                'gastrointestinal': {
                    'lifestyle': ['Eat smaller, frequent meals', 'Avoid trigger foods', 'Manage stress'],
                    'diet': ['High fiber foods', 'Probiotic-rich foods', 'Plenty of water'],
                    'exercise': ['Light walking', 'Yoga', 'Core strengthening']
                },
                'mental_health': {
                    'lifestyle': ['Regular sleep schedule', 'Social connections', 'Mindfulness practice'],
                    'diet': ['Balanced nutrition', 'Limit caffeine and alcohol'],
                    'exercise': ['Regular physical activity', 'Outdoor activities', 'Mind-body exercises']
                }
            },
            'general_health': {
                'daily_habits': [
                    'Get 7-9 hours of sleep nightly',
                    'Drink 8 glasses of water daily',
                    'Eat 5 servings of fruits and vegetables',
                    'Exercise for 30 minutes daily',
                    'Practice stress management techniques'
                ],
                'preventive_care': [
                    'Annual physical examination',
                    'Age-appropriate screenings',
                    'Keep vaccinations up to date',
                    'Dental checkups every 6 months',
                    'Eye exams every 1-2 years'
                ],
                'lifestyle_modifications': [
                    'Maintain healthy weight',
                    'Limit alcohol consumption',
                    'Avoid tobacco products',
                    'Practice safe sun exposure',
                    'Use seatbelts and helmets'
                ]
            }
        }
    
    async def get_recommendations(self, conversation_history: List[Dict]) -> List[str]:
        """Generate recommendations based on conversation history"""
        try:
            if not conversation_history:
                return self._get_general_recommendations()
            
            # Analyze last user message for symptoms
            last_message = conversation_history[-1]
            if last_message.get('role') == 'user':
                content = last_message.get('content', '').lower()
                symptoms = self._extract_symptoms(content)
                
                if symptoms:
                    return self._get_symptom_based_recommendations(symptoms)
            
            return self._get_general_recommendations()
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return self._get_general_recommendations()
    
    async def get_doctor_recommendations(self, symptoms: List[str], 
                                          specialty: Optional[str] = None,
                                          location: Optional[str] = None) -> Dict[str, Any]:
        """Get doctor recommendations based on symptoms"""
        try:
            # Determine specialty based on symptoms
            recommended_specialty = specialty or self._determine_specialty(symptoms)
            
            # Generate recommendations
            recommendations = {
                'preferred_specialties': [recommended_specialty] if recommended_specialty else [],
                'recommendations': [],
                'urgency': 'low'
            }
            
            # Add specific recommendations
            if symptoms:
                symptom_recommendations = self._get_symptom_based_recommendations(symptoms)
                recommendations['recommendations'].extend(symptom_recommendations)
            
            # Determine urgency
            urgency = self._determine_urgency(symptoms)
            recommendations['urgency'] = urgency
            
            # Add urgency-based recommendations
            if urgency == 'high':
                recommendations['recommendations'].append(
                    'Consider seeking immediate medical attention',
                )
            elif urgency == 'medium':
                recommendations['recommendations'].append(
                    'Schedule an appointment within the next few days',
                )
            else:
                recommendations['recommendations'].append(
                    'Regular appointment scheduling is appropriate',
                )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in doctor recommendations: {str(e)}")
            return {
                'preferred_specialties': [],
                'recommendations': [],
                'urgency': 'low'
            }
    
    async def get_lifestyle_recommendations(self, condition: Optional[str] = None,
                                            symptoms: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get lifestyle recommendations for specific condition or symptoms"""
        try:
            recommendations = {
                'immediate': [],
                'lifestyle': [],
                'diet': [],
                'exercise': [],
                'daily_habits': []
            }
            
            if condition and condition in self.recommendation_db['conditions']:
                condition_recs = self.recommendation_db['conditions'][condition]
                recommendations['lifestyle'].extend(condition_recs.get('lifestyle', []))
                recommendations['diet'].extend(condition_recs.get('diet', []))
                recommendations['exercise'].extend(condition_recs.get('exercise', []))
            
            if symptoms:
                for symptom in symptoms:
                    if symptom in self.recommendation_db['symptoms']:
                        symptom_recs = self.recommendation_db['symptoms'][symptom]
                        recommendations['immediate'].extend(symptom_recs.get('immediate', []))
                        recommendations['lifestyle'].extend(symptom_recs.get('lifestyle', []))
                        recommendations['warnings'] = symptom_recs.get('warnings', [])
            
            # Add general health recommendations
            recommendations['daily_habits'].extend(
                self.recommendation_db['general_health']['daily_habits']
            )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating lifestyle recommendations: {str(e)}")
            return {'immediate': [], 'lifestyle': [], 'diet': [], 'exercise': [], 'daily_habits': []}
    
    def _extract_symptoms(self, text: str) -> List[str]:
        """Extract symptoms from text"""
        common_symptoms = [
            'fever', 'cough', 'headache', 'fatigue', 'nausea', 'vomiting',
            'diarrhea', 'chest pain', 'shortness of breath', 'dizziness',
            'sore throat', 'runny nose', 'body ache', 'rash', 'joint pain',
            'abdominal pain', 'back pain', 'muscle weakness', 'weight loss'
        ]
        
        found_symptoms = []
        for symptom in common_symptoms:
            if symptom in text:
                found_symptoms.append(symptom)
        
        return found_symptoms
    
    def _determine_specialty(self, symptoms: List[str]) -> Optional[str]:
        """Determine medical specialty based on symptoms"""
        symptom_categories = {
            'CARDIOLOGY': ['chest pain', 'shortness of breath', 'dizziness'],
            'PULMONOLOGY': ['cough', 'shortness of breath', 'chest pain'],
            'GASTROENTEROLOGY': ['nausea', 'vomiting', 'diarrhea', 'abdominal pain'],
            'NEUROLOGY': ['headache', 'dizziness', 'muscle weakness'],
            'GENERAL_PRACTICE': ['fever', 'fatigue', 'body ache', 'sore throat', 'runny nose'],
            'DERMATOLOGY': ['rash'],
            'ORTHOPEDICS': ['joint pain', 'back pain'],
            'ENDOCRINOLOGY': ['weight loss']
        }
        
        symptom_text = ' '.join(symptoms).lower()
        
        for specialty, specialty_symptoms in symptom_categories.items():
            if any(s in symptom_text for s in specialty_symptoms):
                return specialty
        
        return 'GENERAL_PRACTICE'
    
    def _determine_urgency(self, symptoms: List[str]) -> str:
        """Determine urgency level based on symptoms"""
        urgent_symptoms = [
            'chest pain', 'shortness of breath', 'severe pain',
            'difficulty breathing', 'severe bleeding', 'loss of consciousness'
        ]
        
        symptom_text = ' '.join(symptoms).lower()
        
        if any(urgent in symptom_text for urgent in urgent_symptoms):
            return 'high'
        elif len(symptoms) > 3:
            return 'medium'
        else:
            return 'low'
    
    def _get_symptom_based_recommendations(self, symptoms: List[str]) -> List[str]:
        """Get recommendations based on symptoms"""
        recommendations = []
        
        for symptom in symptoms:
            if symptom in self.recommendation_db['symptoms']:
                symptom_recs = self.recommendation_db['symptoms'][symptom]
                recommendations.extend(symptom_recs.get('immediate', []))
                recommendations.extend(symptom_recs.get('lifestyle', []))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations[:5]  # Return top 5
    
    def _get_general_recommendations(self) -> List[str]:
        """Get general health recommendations"""
        return self.recommendation_db['general_health']['daily_habits'][:3]

# Global instance
recommendation_service = RecommendationService()