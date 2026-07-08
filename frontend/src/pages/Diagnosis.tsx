import { useState } from 'react'
import { diagnosisAPI } from '../services/api'
import { Search, AlertTriangle, CheckCircle, Loader } from 'lucide-react'

interface DiagnosisResult {
  possible_conditions: Array<{
    name: string
    confidence: number
    category: string
  }>
  severity: string
  urgency: string
  advice: string[]
  symptoms: string[]
}

const Diagnosis = () => {
  const [symptoms, setSymptoms] = useState<string[]>([])
  const [currentSymptom, setCurrentSymptom] = useState('')
  const [age, setAge] = useState('')
  const [gender, setGender] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<DiagnosisResult | null>(null)
  const [error, setError] = useState('')

  const commonSymptoms = [
    'Fever', 'Headache', 'Cough', 'Fatigue', 'Nausea', 'Chest Pain',
    'Shortness of Breath', 'Abdominal Pain', 'Joint Pain', 'Skin Rash'
  ]

  const addSymptom = (symptom: string) => {
    if (symptom && !symptoms.includes(symptom)) {
      setSymptoms([...symptoms, symptom])
      setCurrentSymptom('')
    }
  }

  const removeSymptom = (symptom: string) => {
    setSymptoms(symptoms.filter(s => s !== symptom))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (symptoms.length === 0 || !age || !gender) {
      setError('Please fill in all required fields')
      return
    }

    setIsLoading(true)
    setError('')
    setResult(null)

    try {
      const response = await diagnosisAPI.assess({
        symptoms,
        patient_age: parseInt(age),
        patient_gender: gender,
        medical_history: []
      })
      setResult(response.data)
    } catch (err) {
      setError('Failed to get diagnosis. Please try again.')
      console.error('Diagnosis error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'high': return 'text-red-600 bg-red-50 border-red-200'
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      default: return 'text-green-600 bg-green-50 border-green-200'
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="text-center">
        <Search className="h-12 w-12 text-blue-600 mx-auto mb-4" />
        <h1 className="text-3xl font-bold text-gray-900 mb-4">Symptom Analysis</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Describe your symptoms and get AI-powered analysis to understand possible conditions
          and next steps for your health.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Patient Information */}
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Age *
              </label>
              <input
                type="number"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter your age"
                min="1"
                max="120"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Gender *
              </label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="">Select gender</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>

          {/* Symptoms Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Symptoms *
            </label>
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={currentSymptom}
                onChange={(e) => setCurrentSymptom(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addSymptom(currentSymptom))}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter a symptom..."
              />
              <button
                type="button"
                onClick={() => addSymptom(currentSymptom)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Add
              </button>
            </div>

            {/* Common symptoms */}
            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">Common symptoms:</p>
              <div className="flex flex-wrap gap-2">
                {commonSymptoms.map(symptom => (
                  <button
                    key={symptom}
                    type="button"
                    onClick={() => addSymptom(symptom)}
                    className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200"
                  >
                    {symptom}
                  </button>
                ))}
              </div>
            </div>

            {/* Selected symptoms */}
            {symptoms.length > 0 && (
              <div>
                <p className="text-sm text-gray-600 mb-2">Selected symptoms:</p>
                <div className="flex flex-wrap gap-2">
                  {symptoms.map(symptom => (
                    <span
                      key={symptom}
                      className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800"
                    >
                      {symptom}
                      <button
                        type="button"
                        onClick={() => removeSymptom(symptom)}
                        className="ml-2 text-blue-600 hover:text-blue-800"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || symptoms.length === 0}
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center"
          >
            {isLoading ? (
              <>
                <Loader className="animate-spin h-5 w-5 mr-2" />
                Analyzing...
              </>
            ) : (
              <>
                <Search className="h-5 w-5 mr-2" />
                Analyze Symptoms
              </>
            )}
          </button>
        </form>
      </div>

      {/* Results */}
      {result && (
        <div className="bg-white rounded-lg shadow-md p-6 space-y-6">
          <h2 className="text-2xl font-bold text-gray-900">Analysis Results</h2>

          {/* Urgency Level */}
          <div className={`p-4 border rounded-md ${getUrgencyColor(result.urgency)}`}>
            <div className="flex items-center">
              {result.urgency === 'high' ? (
                <AlertTriangle className="h-5 w-5 mr-2" />
              ) : (
                <CheckCircle className="h-5 w-5 mr-2" />
              )}
              <span className="font-semibold capitalize">
                {result.urgency} Priority - {result.severity} Severity
              </span>
            </div>
          </div>

          {/* Possible Conditions */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Possible Conditions</h3>
            <div className="space-y-3">
              {result.possible_conditions.slice(0, 5).map((condition, index) => (
                <div key={index} className="flex justify-between items-center p-3 bg-gray-50 rounded-md">
                  <span className="font-medium">{condition.name}</span>
                  <span className="text-sm text-gray-600">
                    {Math.round(condition.confidence * 100)}% confidence
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Recommendations */}
          {result.advice.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Recommendations</h3>
              <ul className="space-y-2">
                {result.advice.map((advice, index) => (
                  <li key={index} className="flex items-start">
                    <CheckCircle className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                    <span>{advice}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="border-t pt-4">
            <p className="text-sm text-gray-600">
              <strong>Important:</strong> This is not a medical diagnosis. Please consult with a healthcare professional
              for proper medical advice and treatment.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default Diagnosis