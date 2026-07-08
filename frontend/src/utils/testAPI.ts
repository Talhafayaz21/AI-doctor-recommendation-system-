import { doctorsAPI } from "../services/api";

// Test function to verify API connection
export const testAPIConnection = async () => {
  try {
    console.log('Testing API connection...')

    // Test specialties endpoint
    const specialtiesResponse = await doctorsAPI.getSpecialties()
    console.log('Specialties:', specialtiesResponse.data.specialties.length, 'found')

    // Test doctor search
    const doctorsResponse = await doctorsAPI.search({ specialty: 'Cardiology', location: 'Islamabad' })
    console.log('Doctors found:', doctorsResponse.data.doctors.length)

    console.log('✅ API connection successful!')
    return true
  } catch (error) {
    console.error('❌ API connection failed:', error)
    return false
  }
}