import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { doctorsAPI } from '../services/api'
import { Star, MapPin, Clock, Phone, Mail, Award, Languages, Calendar, CheckCircle } from 'lucide-react'

interface Doctor {
  id: string
  name: string
  specialty: string
  sub_specialty?: string
  city: string
  hospital: string
  rating: number
  experience_years: number
  consultation_fee: number
  languages: string[]
  insurance_accepted: string[]
  available_slots: number
  education?: string
  certifications?: string[]
  phone?: string
  telemedicine: boolean
}

interface Availability {
  date: string
  times: string[]
}

const DoctorDetails = () => {
  const { id } = useParams<{ id: string }>()
  const [doctor, setDoctor] = useState<Doctor | null>(null)
  const [availability, setAvailability] = useState<Availability[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedDate, setSelectedDate] = useState('')
  const [selectedTime, setSelectedTime] = useState('')
  const [bookingLoading, setBookingLoading] = useState(false)
  const [bookingSuccess, setBookingSuccess] = useState(false)

  useEffect(() => {
    if (id) {
      fetchDoctorDetails()
    }
  }, [id])

  const fetchDoctorDetails = async () => {
    try {
      setLoading(true)
      const [doctorResponse, availabilityResponse] = await Promise.all([
        doctorsAPI.getById(id!),
        doctorsAPI.getAvailability(id!, new Date().toISOString().split('T')[0])
      ])

      setDoctor(doctorResponse.data.doctor)
      setAvailability(availabilityResponse.data.available_slots || [])
    } catch (error) {
      console.error('Error fetching doctor details:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleBooking = async () => {
    if (!selectedDate || !selectedTime) return

    setBookingLoading(true)
    try {
      await doctorsAPI.bookAppointment({
        doctor_id: id!,
        patient_id: 'pat_001', // In a real app, this would come from user session
        date: selectedDate,
        time: selectedTime,
        reason: 'Consultation appointment'
      })
      setBookingSuccess(true)
      // Refresh availability
      fetchDoctorDetails()
    } catch (error) {
      console.error('Error booking appointment:', error)
      alert('Failed to book appointment. Please try again.')
    } finally {
      setBookingLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Loading doctor details...</p>
      </div>
    )
  }

  if (!doctor) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-600">Doctor not found.</p>
        <Link to="/doctors" className="text-blue-600 hover:text-blue-700">
          Back to doctors
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Doctor Header */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between">
          <div className="flex-1">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{doctor.name}</h1>
                <p className="text-blue-600 font-medium">{doctor.specialty}</p>
                {doctor.sub_specialty && (
                  <p className="text-gray-600">{doctor.sub_specialty}</p>
                )}
              </div>
              <div className="flex items-center">
                <Star className="h-5 w-5 text-yellow-400 fill-current" />
                <span className="text-lg font-semibold ml-1">{doctor.rating}</span>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4 mb-4">
              <div className="flex items-center text-gray-600">
                <MapPin className="h-4 w-4 mr-2" />
                <span>{doctor.hospital}, {doctor.city}</span>
              </div>
              <div className="flex items-center text-gray-600">
                <Clock className="h-4 w-4 mr-2" />
                <span>{doctor.experience_years} years experience</span>
              </div>
              {doctor.phone && (
                <div className="flex items-center text-gray-600">
                  <Phone className="h-4 w-4 mr-2" />
                  <span>{doctor.phone}</span>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between">
              <div className="text-2xl font-bold text-green-600">
                Rs. {doctor.consultation_fee}
              </div>
              <div className="flex gap-2">
                {doctor.telemedicine && (
                  <span className="px-3 py-1 text-sm bg-green-100 text-green-800 rounded-full">
                    Telemedicine Available
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {/* Doctor Information */}
        <div className="md:col-span-2 space-y-6">
          {/* Languages */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center mb-4">
              <Languages className="h-5 w-5 text-blue-600 mr-2" />
              <h2 className="text-lg font-semibold">Languages</h2>
            </div>
            <div className="flex flex-wrap gap-2">
              {doctor.languages.map(lang => (
                <span key={lang} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                  {lang}
                </span>
              ))}
            </div>
          </div>

          {/* Insurance */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-lg font-semibold mb-4">Accepted Insurance</h2>
            <div className="flex flex-wrap gap-2">
              {doctor.insurance_accepted.map(insurance => (
                <span key={insurance} className="px-3 py-1 bg-gray-100 text-gray-700 rounded text-sm">
                  {insurance}
                </span>
              ))}
            </div>
          </div>

          {/* Education & Certifications */}
          {(doctor.education || doctor.certifications) && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center mb-4">
                <Award className="h-5 w-5 text-blue-600 mr-2" />
                <h2 className="text-lg font-semibold">Qualifications</h2>
              </div>
              {doctor.education && (
                <div className="mb-4">
                  <h3 className="font-medium text-gray-900 mb-2">Education</h3>
                  <p className="text-gray-600">{doctor.education}</p>
                </div>
              )}
              {doctor.certifications && doctor.certifications.length > 0 && (
                <div>
                  <h3 className="font-medium text-gray-900 mb-2">Certifications</h3>
                  <ul className="list-disc list-inside text-gray-600">
                    {doctor.certifications.map(cert => (
                      <li key={cert}>{cert}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Booking Section */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center mb-4">
            <Calendar className="h-5 w-5 text-blue-600 mr-2" />
            <h2 className="text-lg font-semibold">Book Appointment</h2>
          </div>

          {bookingSuccess ? (
            <div className="text-center">
              <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-green-600 mb-2">Appointment Booked!</h3>
              <p className="text-gray-600 mb-4">
                Your appointment has been confirmed for {selectedDate} at {selectedTime}.
              </p>
              <Link
                to="/appointments"
                className="bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
              >
                View Appointments
              </Link>
            </div>
          ) : (
            <>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Select Date
                  </label>
                  <select
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Choose a date</option>
                    {availability.map(slot => (
                      <option key={slot.date} value={slot.date}>
                        {new Date(slot.date).toLocaleDateString()}
                      </option>
                    ))}
                  </select>
                </div>

                {selectedDate && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Select Time
                    </label>
                    <select
                      value={selectedTime}
                      onChange={(e) => setSelectedTime(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Choose a time</option>
                      {availability
                        .find(slot => slot.date === selectedDate)
                        ?.times.map(time => (
                          <option key={time} value={time}>{time}</option>
                        ))}
                    </select>
                  </div>
                )}

                <button
                  onClick={handleBooking}
                  disabled={!selectedDate || !selectedTime || bookingLoading}
                  className="w-full bg-blue-600 text-white py-3 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  {bookingLoading ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  ) : (
                    'Book Appointment'
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default DoctorDetails