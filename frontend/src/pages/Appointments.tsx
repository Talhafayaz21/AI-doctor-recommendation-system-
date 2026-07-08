import { useState, useEffect } from 'react'
import { Calendar, Clock, MapPin, User, Phone } from 'lucide-react'

interface Appointment {
  id: string
  doctor_id: string
  patient_id: string
  date: string
  time: string
  reason: string
  symptoms?: string[]
  status: string
  notes?: string
  created_at: string
  doctor_name?: string
  doctor_specialty?: string
  doctor_hospital?: string
}

const Appointments = () => {
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAppointments()
  }, [])

  const fetchAppointments = async () => {
    try {
      setLoading(true)
      // In a real app, this would fetch from the backend
      // For now, we'll simulate some sample appointments
      const sampleAppointments: Appointment[] = [
        {
          id: 'appt_001',
          doctor_id: 'doc_001',
          patient_id: 'pat_001',
          date: '2024-12-15',
          time: '10:00',
          reason: 'Regular checkup',
          status: 'confirmed',
          created_at: '2024-12-01T09:00:00Z',
          doctor_name: 'Dr. Syed Zubair Ahmed',
          doctor_specialty: 'Cardiology',
          doctor_hospital: 'Pakistan Institute of Medical Sciences (PIMS)'
        },
        {
          id: 'appt_002',
          doctor_id: 'doc_006',
          patient_id: 'pat_001',
          date: '2024-12-20',
          time: '14:00',
          reason: 'Follow-up consultation',
          symptoms: ['Cough', 'Fever'],
          status: 'scheduled',
          created_at: '2024-12-10T14:30:00Z',
          doctor_name: 'Dr. Muhammad Irfan',
          doctor_specialty: 'Pulmonology',
          doctor_hospital: 'Gulab Devi Chest Hospital'
        }
      ]
      setAppointments(sampleAppointments)
    } catch (error) {
      console.error('Error fetching appointments:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'confirmed': return 'bg-green-100 text-green-800'
      case 'scheduled': return 'bg-blue-100 text-blue-800'
      case 'completed': return 'bg-gray-100 text-gray-800'
      case 'cancelled': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Loading appointments...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <Calendar className="h-12 w-12 text-blue-600 mx-auto mb-4" />
        <h1 className="text-3xl font-bold text-gray-900 mb-4">My Appointments</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">
          View and manage your upcoming and past appointments with healthcare providers.
        </p>
      </div>

      {appointments.length === 0 ? (
        <div className="text-center py-12">
          <Calendar className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No appointments yet</h3>
          <p className="text-gray-600 mb-4">
            You haven't booked any appointments. Start by finding a doctor that meets your needs.
          </p>
          <a
            href="/doctors"
            className="bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
          >
            Find Doctors
          </a>
        </div>
      ) : (
        <div className="grid gap-6">
          {appointments.map(appointment => (
            <div key={appointment.id} className="bg-white rounded-lg shadow-md p-6">
              <div className="flex flex-col md:flex-row md:items-start md:justify-between">
                <div className="flex-1">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {appointment.doctor_name}
                      </h3>
                      <p className="text-blue-600">{appointment.doctor_specialty}</p>
                      <p className="text-gray-600 text-sm">{appointment.doctor_hospital}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${getStatusColor(appointment.status)}`}>
                      {appointment.status}
                    </span>
                  </div>

                  <div className="grid md:grid-cols-2 gap-4 mb-4">
                    <div className="flex items-center text-gray-600">
                      <Calendar className="h-4 w-4 mr-2" />
                      <span>{formatDate(appointment.date)}</span>
                    </div>
                    <div className="flex items-center text-gray-600">
                      <Clock className="h-4 w-4 mr-2" />
                      <span>{appointment.time}</span>
                    </div>
                  </div>

                  <div className="mb-4">
                    <p className="text-sm text-gray-700">
                      <strong>Reason:</strong> {appointment.reason}
                    </p>
                    {appointment.symptoms && appointment.symptoms.length > 0 && (
                      <p className="text-sm text-gray-700 mt-2">
                        <strong>Symptoms:</strong> {appointment.symptoms.join(', ')}
                      </p>
                    )}
                  </div>

                  {appointment.notes && (
                    <div className="mb-4">
                      <p className="text-sm text-gray-700">
                        <strong>Notes:</strong> {appointment.notes}
                      </p>
                    </div>
                  )}
                </div>

                <div className="mt-4 md:mt-0 md:ml-6 flex flex-col gap-2">
                  <button className="bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 text-sm">
                    View Details
                  </button>
                  {appointment.status === 'scheduled' && (
                    <button className="bg-red-600 text-white py-2 px-4 rounded-md hover:bg-red-700 text-sm">
                      Cancel
                    </button>
                  )}
                  <button className="bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 text-sm">
                    Reschedule
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Appointments