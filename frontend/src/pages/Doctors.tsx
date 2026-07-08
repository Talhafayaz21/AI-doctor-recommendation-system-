import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { doctorsAPI } from '../services/api'
import { Search, MapPin, Star, Clock, Phone } from 'lucide-react'

interface Doctor {
  id: string
  name: string
  specialty: string
  city: string
  hospital: string
  rating: number
  experience_years: number
  consultation_fee: number
  languages: string[]
  telemedicine: boolean
}

const Doctors = () => {
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedSpecialty, setSelectedSpecialty] = useState('')
  const [selectedCity, setSelectedCity] = useState('')
  const [specialties, setSpecialties] = useState<string[]>([])

  const cities = [
    'Islamabad', 'Karachi', 'Lahore', 'Rawalpindi', 'Peshawar',
    'Quetta', 'Multan', 'Faisalabad', 'Hyderabad', 'Sialkot'
  ]

  useEffect(() => {
    fetchSpecialties()
    fetchDoctors()
  }, [])

  const fetchSpecialties = async () => {
    try {
      const response = await doctorsAPI.getSpecialties()
      setSpecialties(response.data.specialties)
    } catch (error) {
      console.error('Error fetching specialties:', error)
    }
  }

  const fetchDoctors = async () => {
    try {
      setLoading(true)
      const params = {
        specialty: selectedSpecialty || undefined,
        location: selectedCity || undefined,
        symptoms: searchTerm || undefined
      }
      const response = await doctorsAPI.search(params)
      setDoctors(response.data.doctors)
    } catch (error) {
      console.error('Error fetching doctors:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    fetchDoctors()
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <Search className="h-12 w-12 text-blue-600 mx-auto mb-4" />
        <h1 className="text-3xl font-bold text-gray-900 mb-4">Find Doctors</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Search for qualified healthcare professionals in your area based on specialty,
          location, and your specific health needs.
        </p>
      </div>

      {/* Search Filters */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="grid md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Specialty
            </label>
            <select
              value={selectedSpecialty}
              onChange={(e) => setSelectedSpecialty(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Specialties</option>
              {specialties.map(specialty => (
                <option key={specialty} value={specialty}>{specialty}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              City
            </label>
            <select
              value={selectedCity}
              onChange={(e) => setSelectedCity(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Cities</option>
              {cities.map(city => (
                <option key={city} value={city}>{city}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Symptoms/Condition
            </label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={handleKeyPress}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., fever, headache"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={handleSearch}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 flex items-center justify-center"
            >
              <Search className="h-4 w-4 mr-2" />
              Search
            </button>
          </div>
        </div>
      </div>

      {/* Results */}
      {loading ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading doctors...</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {doctors.map(doctor => (
            <div key={doctor.id} className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">{doctor.name}</h3>
                  <p className="text-blue-600 font-medium">{doctor.specialty}</p>
                </div>
                <div className="flex items-center">
                  <Star className="h-4 w-4 text-yellow-400 fill-current" />
                  <span className="text-sm text-gray-600 ml-1">{doctor.rating}</span>
                </div>
              </div>

              <div className="space-y-2 mb-4">
                <div className="flex items-center text-gray-600">
                  <MapPin className="h-4 w-4 mr-2" />
                  <span className="text-sm">{doctor.city}</span>
                </div>
                <div className="flex items-center text-gray-600">
                  <Clock className="h-4 w-4 mr-2" />
                  <span className="text-sm">{doctor.experience_years} years experience</span>
                </div>
                <div className="text-sm text-gray-600">
                  {doctor.hospital}
                </div>
              </div>

              <div className="flex items-center justify-between mb-4">
                <div className="text-lg font-semibold text-green-600">
                  Rs. {doctor.consultation_fee}
                </div>
                {doctor.telemedicine && (
                  <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">
                    Telemedicine
                  </span>
                )}
              </div>

              <div className="flex flex-wrap gap-1 mb-4">
                {doctor.languages.slice(0, 3).map(lang => (
                  <span key={lang} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                    {lang}
                  </span>
                ))}
              </div>

              <Link
                to={`/doctors/${doctor.id}`}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 text-center block"
              >
                View Details
              </Link>
            </div>
          ))}
        </div>
      )}

      {!loading && doctors.length === 0 && (
        <div className="text-center py-8">
          <p className="text-gray-600">No doctors found matching your criteria. Try adjusting your search.</p>
        </div>
      )}
    </div>
  )
}

export default Doctors