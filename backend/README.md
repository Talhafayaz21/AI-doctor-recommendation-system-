# Care Companion Backend API

## Overview
AI-powered healthcare assistant backend built with FastAPI, providing intelligent symptom analysis, diagnosis assistance, doctor recommendations, and personalized health recommendations.

## Features

### 1. Chat Module (`/api/chat`)
- Conversational AI for health-related queries
- Streamed responses for better UX
- Session-based conversation history
- Real-time symptom analysis

### 2. Diagnosis Module (`/api/diagnosis`)
- AI-powered symptom analysis
- ML-based disease prediction
- Differential diagnosis generation
- Urgency level assessment
- Condition information lookup

### 3. Doctors Module (`/api/doctors`)
- Doctor search and filtering
- AI-powered recommendations
- Appointment booking
- Availability checking
- Specialty-based matching

## Architecture

### Backend Stack
- **Framework**: FastAPI (async, high-performance)
- **Language**: Python 3.10+
- **LLM**: OpenAI GPT-4 (or configurable)
- **ML**: Scikit-learn with pickled models
- **Database**: PostgreSQL (asyncpg)
- **Cache**: Redis (optional)
- **API Docs**: Swagger/ReDoc (auto-generated)

### Core Components

#### Agents
- **SymptomAgent**: Intelligent symptom analysis and understanding
- **DiagnosisAgent**: Diagnosis assistance and medical analysis
- **RecommendationAgent**: Personalized health recommendations
- **SafetyAgent**: Content filtering and safety checks

#### Services
- **LLMService**: OpenAI integration for conversational AI
- **PredictionService**: ML-based disease prediction
- **RecommendationService**: Health and lifestyle recommendations

#### Routes
- **ChatRouter**: Conversation endpoints
- **DiagnosisRouter**: Diagnosis and symptom analysis
- **DoctorsRouter**: Doctor search and appointment booking

## API Endpoints

### Chat Endpoints
- `POST /api/chat/conversation` - Process chat conversation
- `POST /api/chat/stream` - Stream response
- `GET /api/chat/history/{session_id}` - Get chat history
- `POST /api/chat/analyze-symptoms` - Analyze symptoms

### Diagnosis Endpoints
- `POST /api/diagnosis/assess` - Assess diagnosis
- `POST /api/diagnosis/predict` - Predict conditions
- `GET /api/diagnosis/conditions/{id}` - Get condition details
- `GET /api/diagnosis/urgency-calculator` - Calculate urgency

### Doctor Endpoints
- `GET /api/doctors/search` - Search doctors
- `POST /api/doctors/recommend` - Get recommendations
- `POST /api/doctors/book` - Book appointment
- `GET /api/doctors/availability/{id}` - Check availability
- `GET /api/doctors/{id}` - Get doctor details

## Setup & Installation

### Prerequisites
```bash
# Python 3.10 or higher
# PostgreSQL 14+
# Redis (optional)
```

### Installation

1. Clone the repository
2. Navigate to backend directory
3. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Copy environment template:
```bash
cp .env.template .env
```

6. Edit `.env` with your configuration

### Database Setup
```bash
# Create PostgreSQL database
createdb care_companion

# Or with docker:
docker run -d --name postgres -e POSTGRES_DB=care_companion -p 5432:5432 postgres:14
```

## Running the Application

### Development Mode
```bash
python run.py
```

### Production Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Auto-generated docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | - |
| `DATABASE_URL` | PostgreSQL connection string | postgresql://... |
| `REDIS_URL` | Redis connection string | redis://localhost:6379 |
| `OPENAI_MODEL` | OpenAI model to use | gpt-4o-mini |
| `DEBUG` | Debug mode | True |
| `LOG_LEVEL` | Logging level | INFO |

## Testing

```bash
# Run tests
pytest tests/

# Run specific test
pytest tests/test_chat.py -v
```

## Security Features

- Input validation with Pydantic
- SQL injection protection
- Rate limiting
- Content safety checks
- Emergency keyword detection
- Self-harm risk assessment
- Medical disclaimer enforcement

## Performance

- Async request handling
- Database connection pooling
- Redis caching (optional)
- Optimized ML model loading
- Response streaming support

## Contributing

1. Follow existing code style
2. Add tests for new features
3. Update documentation
4. Ensure all tests pass

## License

MIT License

## Support

For issues or questions, please contact the development team.