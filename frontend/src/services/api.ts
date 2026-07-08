import axios from 'axios'

const API_BASE_URL =
  `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api`

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ─────────────────────────────────────────────
// Diagnosis API
// ─────────────────────────────────────────────
export const diagnosisAPI = {
  assess: (data: {
    symptoms: string[]
    patient_age: number
    patient_gender: string
    medical_history?: string[]
  }) =>
    api.post('/diagnosis/assess', data),

  predict: (data: {
    symptoms: string[]
    patient_age: number
    patient_gender: string
    medical_history?: string[]
  }) =>
    api.post('/diagnosis/predict', data),
}

// ─────────────────────────────────────────────
// Doctors API
// ─────────────────────────────────────────────
export const doctorsAPI = {
  search: (params?: {
    specialty?: string
    location?: string
    symptoms?: string
    language?: string
    insurance?: string
  }) =>
    api.get('/doctors/search', { params }),

  getById: (id: string) =>
    api.get(`/doctors/${id}`),

  getAvailability: (
    id: string,
    startDate: string,
    endDate?: string
  ) =>
    api.get(`/doctors/availability/${id}`, {
      params: {
        start_date: startDate,
        end_date: endDate,
      },
    }),

  getSpecialties: () =>
    api.get('/doctors/specialties'),

  bookAppointment: (data: {
    doctor_id: string
    patient_id: string
    date: string
    time: string
    reason: string
    symptoms?: string[]
  }) =>
    api.post('/doctors/book', data),
}

// ─────────────────────────────────────────────
// Chat API
// ─────────────────────────────────────────────
export const chatAPI = {
  converse: (data: {
    message: string
    message_history?: Array<{
      role: string
      content: string
    }>
    orchestrator_result?: object
  }) =>
    api.post('/chat/conversation', {
      message: data.message,
      message_history: data.message_history || [],
      orchestrator_result: data.orchestrator_result || {},
    }),

  stream: (data: {
    message: string
    message_history?: Array<{
      role: string
      content: string
    }>
    orchestrator_result?: object
  }) =>
    api.post('/chat/stream', {
      message: data.message,
      message_history: data.message_history || [],
      orchestrator_result: data.orchestrator_result || {},
    }),
}

export default api