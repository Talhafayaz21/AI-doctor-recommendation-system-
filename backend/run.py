import uvicorn
from dotenv import load_dotenv
from app.main import app
from app.utils.config import settings

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    print("Starting Care Companion API...")
    print(f"Environment: {'Production' if settings.is_production() else 'Development'}")
    print(f"Debug Mode: {settings.DEBUG}")
    print(f"API available at http://localhost:8000")
    print(f"API docs at http://localhost:8000/docs")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )