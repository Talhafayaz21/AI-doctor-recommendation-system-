# Care Companion - AI Health Assistant

A comprehensive healthcare companion application with AI-powered diagnosis, doctor recommendations, and appointment booking.

## Features

- **AI Symptom Analysis**: Get intelligent analysis of your symptoms using machine learning
- **Doctor Recommendations**: Find qualified healthcare professionals based on specialty, location, and symptoms
- **Appointment Booking**: Schedule appointments with doctors directly through the app
- **AI Chat Support**: Conversational AI assistant for health-related questions
- **Appointment Management**: View and manage your upcoming appointments

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React + TypeScript + Tailwind CSS
- **AI/ML**: Scikit-learn models for disease prediction
- **Database**: Mock database with Pakistani doctor data

## Setup Instructions

### Prerequisites

- Python 3.9+
- Node.js 16+
- VS Code with Python extension configured

### Backend Setup

1. **Install dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   - Copy `.env.template` to `.env`
   - Update API keys and database settings as needed
   - **Important**: Enable VS Code Python terminal env file loading:
     - Open VS Code Settings (Ctrl+,)
     - Search for `python.terminal.useEnvFile`
     - Check the box to enable it

3. **Start the backend**:
   ```bash
   cd backend
   python run.py
   ```
   Backend will be available at `http://localhost:8000`

### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment**:
   - The frontend will automatically use the backend API at `http://localhost:8000`

3. **Start the frontend**:
   ```bash
   cd frontend
   npm run dev
   ```
   Frontend will be available at `http://localhost:5173` (or next available port)

## API Endpoints

### Diagnosis
- `POST /api/diagnosis/assess` - Analyze symptoms and get diagnosis

### Doctors
- `GET /api/doctors/specialties` - Get available specialties
- `GET /api/doctors/search` - Search doctors with filters
- `GET /api/doctors/{id}` - Get doctor details
- `GET /api/doctors/availability/{id}` - Get doctor availability
- `POST /api/doctors/book` - Book appointment

### Chat
- `POST /api/chat/conversation` - Chat with AI assistant

## Usage

1. **Symptom Analysis**: Go to Diagnosis page, enter symptoms, age, and gender
2. **Find Doctors**: Use the Doctors page to search by specialty and location
3. **Book Appointments**: View doctor details and book appointments
4. **AI Chat**: Use the Chat page for health-related conversations
5. **Manage Appointments**: View your appointments in the Appointments page

## Development

- Backend API docs: `http://localhost:8000/docs`
- Frontend dev server: `http://localhost:5173`
- Hot reload enabled for both frontend and backend

## Troubleshooting

### Backend won't start
- Ensure `.env` file exists and environment variables are loaded
- Check if required Python packages are installed
- Verify OpenAI API key is valid

### Frontend connection issues
- Ensure backend is running on port 8000
- Check CORS settings in backend
- Verify `VITE_API_BASE_URL` environment variable

### VS Code Python issues
- Enable `python.terminal.useEnvFile` setting
- Restart VS Code terminals after configuration changes