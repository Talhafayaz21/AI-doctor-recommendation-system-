import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Heart, Search, User, MessageCircle, Calendar, Shield, Brain, Stethoscope } from 'lucide-react'
import { testAPIConnection } from '../utils/testAPI'

const Home = () => {
  const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'error'>('checking')

  useEffect(() => {
    testAPIConnection().then(success => {
      setApiStatus(success ? 'connected' : 'error')
    })
  }, [])

  const features = [
    {
      icon: Search,
      title: 'Symptom Analysis',
      description: 'Get instant analysis of your symptoms with AI-powered diagnosis',
      link: '/diagnosis',
      color: 'bg-blue-500'
    },
    {
      icon: User,
      title: 'Find Doctors',
      description: 'Connect with qualified healthcare professionals in your area',
      link: '/doctors',
      color: 'bg-green-500'
    },
    {
      icon: MessageCircle,
      title: 'AI Chat Support',
      description: '24/7 conversational support for your health concerns',
      link: '/chat',
      color: 'bg-purple-500'
    },
    {
      icon: Calendar,
      title: 'Book Appointments',
      description: 'Schedule appointments with ease and manage your healthcare',
      link: '/appointments',
      color: 'bg-orange-500'
    }
  ]

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center py-16">
        <div className="flex justify-center mb-6">
          <Heart className="h-16 w-16 text-blue-600" />
        </div>
        <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-4">
          Your AI Health Companion
        </h1>
        <div className="mb-4">
          {apiStatus === 'checking' && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-yellow-100 text-yellow-800">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-600 mr-2"></div>
              Connecting to backend...
            </span>
          )}
          {apiStatus === 'connected' && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-green-100 text-green-800">
              <Shield className="h-4 w-4 mr-2" />
              Backend Connected
            </span>
          )}
          {apiStatus === 'error' && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-red-100 text-red-800">
              Backend Connection Error
            </span>
          )}
        </div>
        <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
          Get personalized healthcare guidance, find the right doctors, and manage your health journey
          with our intelligent care companion powered by advanced AI and machine learning.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            to="/diagnosis"
            className="bg-blue-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
          >
            Start Diagnosis
          </Link>
          <Link
            to="/doctors"
            className="bg-white text-blue-600 border-2 border-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-blue-50 transition-colors"
          >
            Find Doctors
          </Link>
        </div>
      </section>

      {/* Features Grid */}
      <section>
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
          How Can We Help You Today?
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map(({ icon: Icon, title, description, link, color }) => (
            <Link
              key={title}
              to={link}
              className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow group"
            >
              <div className={`w-12 h-12 ${color} rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                <Icon className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">{title}</h3>
              <p className="text-gray-600">{description}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* Technology Section */}
      <section className="bg-white rounded-lg shadow-md p-8">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-8">
          Powered by Advanced Technology
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="text-center">
            <Brain className="h-12 w-12 text-blue-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">AI Diagnosis</h3>
            <p className="text-gray-600">
              Machine learning models analyze symptoms to provide accurate preliminary diagnoses
            </p>
          </div>
          <div className="text-center">
            <Stethoscope className="h-12 w-12 text-green-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Doctor Network</h3>
            <p className="text-gray-600">
              Extensive database of qualified healthcare professionals across Pakistan
            </p>
          </div>
          <div className="text-center">
            <Shield className="h-12 w-12 text-purple-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Privacy First</h3>
            <p className="text-gray-600">
              Your health data is secure and confidential, protected by industry standards
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}

export default Home