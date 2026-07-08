import { useState, useRef, useEffect } from 'react'
import { chatAPI } from '../services/api'
import { Send, Bot, User, Loader } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

const Chat = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        "Hello! I'm your AI health companion. How can I help you today? You can describe your symptoms, ask health questions, or get guidance on your wellness journey.",
      timestamp: new Date().toISOString(),
    },
  ])

  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth',
    })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    // Create user message
    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    }

    // Add user message to chat
    setMessages((prev) => [...prev, userMessage])

    // Store current input before clearing
    const currentInput = input

    // Clear input and start loading
    setInput('')
    setIsLoading(true)

    try {
      // Send correct payload to backend
      const response = await chatAPI.converse({
        message: currentInput,
        message_history: messages.map((msg) => ({
          role: msg.role,
          content: msg.content,
        })),
        orchestrator_result: {},
      })

      // Add assistant response
      const assistantMessage: Message = {
        role: 'assistant',
        content:
          response.data.response ||
          'Sorry, I could not generate a response.',
        timestamp: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, assistantMessage])

    } catch (error: any) {
      console.error('Chat error:', error)

      // Show backend validation errors if available
      let errorText =
        "I'm sorry, I encountered an error. Please try again."

      if (error?.response?.data?.detail) {
        errorText =
          typeof error.response.data.detail === 'string'
            ? error.response.data.detail
            : JSON.stringify(error.response.data.detail)
      }

      const errorMessage: Message = {
        role: 'assistant',
        content: errorText,
        timestamp: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, errorMessage])

    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (
    e: React.KeyboardEvent<HTMLTextAreaElement>
  ) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="text-center mb-6">
        <Bot className="h-12 w-12 text-blue-600 mx-auto mb-4" />

        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          AI Health Assistant
        </h1>

        <p className="text-gray-600">
          Chat with our AI companion for health guidance,
          symptom analysis, and wellness advice.
        </p>
      </div>

      {/* Chat Container */}
      <div className="bg-white rounded-lg shadow-md h-[600px] flex flex-col">

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">

          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${
                message.role === 'user'
                  ? 'justify-end'
                  : 'justify-start'
              }`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                {/* Message Header */}
                <div className="flex items-center mb-1">
                  {message.role === 'user' ? (
                    <User className="h-4 w-4 mr-2" />
                  ) : (
                    <Bot className="h-4 w-4 mr-2" />
                  )}

                  <span className="text-xs opacity-75">
                    {message.role === 'user'
                      ? 'You'
                      : 'Assistant'}
                  </span>
                </div>

                {/* Message Content */}
                <div className="whitespace-pre-wrap text-sm">
                  {message.content}
                </div>
              </div>
            </div>
          ))}

          {/* Loading */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 text-gray-900 px-4 py-2 rounded-lg">
                <div className="flex items-center">
                  <Bot className="h-4 w-4 mr-2" />

                  <Loader className="h-4 w-4 animate-spin" />

                  <span className="text-sm ml-2">
                    Thinking...
                  </span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t p-4">
          <div className="flex gap-2">

            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Describe your symptoms or ask a health question..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              rows={2}
              disabled={isLoading}
            />

            <button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              className="bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              <Send className="h-5 w-5" />
            </button>

          </div>

          <p className="text-xs text-gray-500 mt-2">
            Press Enter to send, Shift + Enter for new line
          </p>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">

        <h3 className="font-semibold text-yellow-800 mb-2">
          Important Medical Disclaimer
        </h3>

        <p className="text-sm text-yellow-700">
          This AI assistant provides general health information
          and guidance, but it is not a substitute for professional
          medical advice, diagnosis, or treatment. Always consult
          qualified healthcare providers for medical concerns and
          emergencies.
        </p>

      </div>
    </div>
  )
}

export default Chat