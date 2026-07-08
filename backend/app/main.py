from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import chat, diagnosis, doctors, rag
from app.utils.config import settings


app = FastAPI(
    title="Care Companion API",
    description="AI-powered healthcare assistant backend with RAG, ML models, and doctor database",
    version=getattr(settings, "VERSION", "1.0.0"),
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development. Change this in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(diagnosis.router, prefix="/api/diagnosis", tags=["Diagnosis"])
app.include_router(doctors.router, prefix="/api/doctors", tags=["Doctors"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])


@app.get("/")
async def root():
    return {
        "message": "Care Companion API is running",
        "version": getattr(settings, "VERSION", "1.0.0"),
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "running",
            "rag": "available",
            "ml_model": "available",
            "database": "available",
        },
    }