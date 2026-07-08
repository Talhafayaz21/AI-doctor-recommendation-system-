from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
from app.database.db import get_db_connection, get_doctors_by_specialty, get_doctors_by_city, get_doctor_by_id, get_all_doctors
from app.database.doctor_schema import Doctor, DoctorSpecialty, DoctorAvailability

router = APIRouter()

class DoctorSearchRequest(BaseModel):
    specialty: Optional[str] = None
    location: Optional[str] = None
    symptoms: Optional[List[str]] = None
    language: Optional[str] = None
    insurance: Optional[str] = None
    max_distance: Optional[float] = None

class AppointmentRequest(BaseModel):
    doctor_id: str
    patient_id: str
    date: str
    time: str
    reason: str
    symptoms: Optional[List[str]] = None

class DoctorRecommendationResponse(BaseModel):
    doctors: List[Doctor]
    match_scores: List[float]
    recommendations: List[str]
    total_results: int

@router.get("/search")
async def search_doctors(
    specialty: Optional[str] = None,
    location: Optional[str] = None,
    symptoms: Optional[str] = None,
    language: Optional[str] = None,
    insurance: Optional[str] = None
):
    """Search for doctors based on criteria"""
    try:
        # Parse symptoms if provided
        symptom_list = symptoms.split(",") if symptoms else []

        # Create basic recommendations dict (simplified for now)
        recommendations = {
            "preferred_specialties": [specialty] if specialty else [],
            "recommended_specialist": specialty or "General Practitioner"
        }

        # Filter doctors from database
        doctors = await _filter_doctors_from_db(
            specialty=specialty,
            location=location,
            language=language,
            insurance=insurance,
            recommendations=recommendations
        )

        # Calculate match scores
        match_scores = await _calculate_match_scores(doctors, recommendations)

        # Convert doctors to dicts for JSON serialization
        doctors_dict = []
        for doctor in doctors:
            doctor_dict = doctor.model_dump()
            # Convert enum to string
            doctor_dict['specialty'] = doctor_dict['specialty'].value if hasattr(doctor_dict['specialty'], 'value') else str(doctor_dict['specialty'])
            doctors_dict.append(doctor_dict)

        return {
            "doctors": doctors_dict,
            "match_scores": match_scores,
            "recommendations": ["Consider booking soon for better availability"] if len(doctors) > 0 else ["Try broadening search criteria"],
            "total_results": len(doctors)
        }
    except Exception as e:
        logging.error(f"Error searching doctors: {str(e)}")
        raise

@router.post("/recommend")
async def recommend_doctors(request: DoctorSearchRequest):
    """Get doctor recommendations"""
    try:
        # Create basic recommendations dict
        recommendations = {
            "preferred_specialties": [request.specialty] if request.specialty else [],
            "recommended_specialist": request.specialty or "General Practitioner",
            "recommendations": ["Consider booking soon for better availability"]
        }

        doctors = await _filter_doctors_from_db(
            specialty=request.specialty,
            location=request.location,
            language=request.language,
            insurance=request.insurance,
            recommendations=recommendations
        )

        match_scores = await _calculate_match_scores(doctors, recommendations)

        return {
            "doctors": doctors,
            "match_scores": match_scores,
            "recommendations": recommendations.get("recommendations", []),
            "total_results": len(doctors)
        }
    except Exception as e:
        logging.error(f"Error in doctor recommendations: {str(e)}")
        raise

@router.post("/book", response_model=dict)
async def book_appointment(request: AppointmentRequest):
    """Book an appointment with a doctor"""
    try:
        # Check doctor availability
        doctor = await _get_doctor_by_id(request.doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        is_available = await _check_availability(request.doctor_id, request.date, request.time)
        if not is_available:
            raise HTTPException(status_code=409, detail="Time slot not available")
        
        # Create appointment
        appointment_id = await _create_appointment(
            doctor_id=request.doctor_id,
            patient_id=request.patient_id,
            date=request.date,
            time=request.time,
            reason=request.reason,
            symptoms=request.symptoms
        )
        
        return {
            "success": True,
            "appointment_id": appointment_id,
            "message": "Appointment booked successfully",
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error booking appointment: {str(e)}")
        raise

@router.get("/availability/{doctor_id}")
async def get_availability(doctor_id: str, start_date: str, end_date: Optional[str] = None):
    """Get doctor's availability schedule"""
    try:
        availability = await _get_doctor_availability(doctor_id, start_date, end_date)
        return availability
    except Exception as e:
        logging.error(f"Error retrieving availability: {str(e)}")
        raise

@router.get("/specialties")
async def get_specialties():
    """Get list of available medical specialties"""
    try:
        specialties = await _get_all_specialties()
        return {"specialties": specialties}
    except Exception as e:
        logging.error(f"Error retrieving specialties: {str(e)}")
        raise

@router.get("/{doctor_id}")
async def get_doctor_details(doctor_id: str):
    """Get detailed information about a specific doctor"""
    try:
        doctor = await _get_doctor_by_id(doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        availability = await _get_doctor_availability(doctor_id, datetime.now().isoformat())
        
        return {
            "doctor": doctor,
            "availability": availability
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error retrieving doctor details: {str(e)}")
        raise

async def _filter_doctors_from_db(specialty, location, language, insurance, recommendations):
    """Filter doctors from database based on criteria"""
    # Get doctors from actual database
    if specialty:
        doctors_data = await get_doctors_by_specialty(specialty)
    elif location:
        doctors_data = await get_doctors_by_city(location)
    else:
        # If no specific filters, get all doctors (this might need pagination in production)
        from app.database.db import get_all_doctors
        doctors_data = await get_all_doctors()
    
    # Convert database results to Doctor objects
    doctors = []
    for doc_data in doctors_data:
        try:
            doctor = Doctor(
                id=doc_data["id"],
                name=doc_data["name"],
                specialty=DoctorSpecialty(doc_data["specialty"]),
                sub_specialty=doc_data.get("sub_specialty"),
                location=doc_data["location"],
                city=doc_data["city"],
                hospital=doc_data["hospital"],
                rating=float(doc_data["rating"]),
                experience_years=int(doc_data["experience_years"]),
                languages=doc_data["languages"] if isinstance(doc_data["languages"], list) else [],
                insurance_accepted=doc_data["insurance_accepted"] if isinstance(doc_data["insurance_accepted"], list) else [],
                available_slots=int(doc_data["available_slots"]),
                consultation_fee=int(doc_data["consultation_fee"]),
                education=doc_data.get("education"),
                certifications=doc_data.get("certifications", []),
                phone=doc_data.get("phone"),
                telemedicine=bool(doc_data.get("telemedicine", False))
            )
            doctors.append(doctor)
        except Exception as e:
            logging.warning(f"Skipping doctor due to conversion error: {e}")
            continue
    
    # Apply additional filters
    filtered = doctors
    if language:
        filtered = [d for d in filtered if any(lang.lower() == language.lower() for lang in d.languages)]
    if insurance:
        filtered = [d for d in filtered if any(ins.lower() == insurance.lower() for ins in d.insurance_accepted)]
    
    return filtered

async def _calculate_match_scores(doctors, recommendations):
    """Calculate match scores between doctors and recommendations"""
    scores = []
    for doctor in doctors:
        base_score = doctor.rating / 5.0  # Normalize to 0-1
        # Add bonus for specialty match
        if recommendations.get("preferred_specialties"):
            if doctor.specialty.value.lower() in [s.lower() for s in recommendations.get("preferred_specialties", [])]:
                base_score += 0.1
        scores.append(min(base_score, 1.0))
    return scores

async def _get_doctor_by_id(doctor_id: str):
    """Get doctor by ID from database"""
    doctor_data = await get_doctor_by_id(doctor_id)
    if doctor_data:
        return Doctor(
            id=doctor_data["id"],
            name=doctor_data["name"],
            specialty=DoctorSpecialty(doctor_data["specialty"]),
            sub_specialty=doctor_data.get("sub_specialty"),
            location=doctor_data["location"],
            city=doctor_data["city"],
            hospital=doctor_data["hospital"],
            rating=float(doctor_data["rating"]),
            experience_years=int(doctor_data["experience_years"]),
            languages=doctor_data["languages"] if isinstance(doctor_data["languages"], list) else [],
            insurance_accepted=doctor_data["insurance_accepted"] if isinstance(doctor_data["insurance_accepted"], list) else [],
            available_slots=int(doctor_data["available_slots"]),
            consultation_fee=int(doctor_data["consultation_fee"]),
            education=doctor_data.get("education"),
            certifications=doctor_data.get("certifications", []),
            phone=doctor_data.get("phone"),
            telemedicine=bool(doctor_data.get("telemedicine", False))
        )
    return None

async def _check_availability(doctor_id: str, date: str, time: str):
    """Check if doctor is available at specified time"""
    # Get doctor's availability from database
    availability = await _get_doctor_availability(doctor_id, date, date)
    if availability and "available_slots" in availability:
        for slot in availability["available_slots"]:
            if slot.get("date") == date and time in slot.get("times", []):
                return True
    return False

async def _create_appointment(doctor_id, patient_id, date, time, reason, symptoms):
    """Create appointment in database"""
    appointment_data = {
        "doctor_id": doctor_id,
        "patient_id": patient_id,
        "date": date,
        "time": time,
        "reason": reason,
        "symptoms": symptoms
    }
    return await create_appointment(appointment_data)

async def _get_doctor_availability(doctor_id: str, start_date: str, end_date: Optional[str] = None):
    """Get doctor availability from database"""
    doctor = await _get_doctor_by_id(doctor_id)
    if not doctor:
        return {"doctor_id": doctor_id, "available_slots": []}

    # We don't have per-date availability in the database, so we simulate based on available_slots
    # In a real application, you would query an availability table or collection
    from datetime import datetime, timedelta
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date) if end_date else start
    except ValueError:
        # If date parsing fails, return empty availability
        return {"doctor_id": doctor_id, "available_slots": []}
    
    days = (end - start).days + 1
    if days < 1:
        days = 1

    # Default time slots (can be configured or stored per doctor in a real system)
    default_time_slots = ["09:00", "10:00", "14:00", "15:00", "16:00"]
    # Limit slots per day based on doctor's available_slots field (assuming it's slots per day)
    slots_per_day = min(doctor.available_slots, len(default_time_slots))
    time_slots = default_time_slots[:slots_per_day] if slots_per_day > 0 else []

    available_slots = []
    current = start
    while current <= end:
        available_slots.append({
            "date": current.strftime("%Y-%m-%d"),
            "times": time_slots.copy()
        })
        current += timedelta(days=1)

    return {
        "doctor_id": doctor_id,
        "available_slots": available_slots
    }

async def _get_all_specialties():
    """Get all available medical specialties"""
    return [specialty.value for specialty in DoctorSpecialty]