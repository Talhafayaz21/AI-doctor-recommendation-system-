from typing import Optional, List
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv

# --------------------------------------------------
# LOAD ENV FILE (SAFE WAY)
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    print("⚠️ Warning: .env file not found")

# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------
def get_bool(key: str, default: str = "False") -> bool:
    return os.getenv(key, default).lower() == "true"

def get_int(key: str, default: str) -> int:
    try:
        return int(os.getenv(key, default))
    except ValueError:
        return int(default)

# --------------------------------------------------
# SETTINGS CLASS
# --------------------------------------------------
class Settings:
    """Application settings and configuration"""

    # ------------------------
    # BASIC APP CONFIG
    # ------------------------
    APP_NAME: str = "Care Companion API"
    VERSION: str = "1.0.0"
    DEBUG: bool = get_bool("DEBUG", "False")

    API_V1_STR: str = "/api/v1"

    # ------------------------
    # ENVIRONMENT
    # ------------------------
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # ------------------------
    # DATABASE
    # ------------------------
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL", "sqlite:///./mock.db")
    # Note: We're using MOCK_DATABASE for development, so DATABASE_URL is optional

    # ------------------------
    # REDIS
    # ------------------------
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # ------------------------
    # OPENAI / LLM
    # ------------------------
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    # Note: API key is optional - agents will use fallback mode if not provided

    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_API_BASE: Optional[str] = os.getenv("OPENAI_API_BASE")

    # ------------------------
    # ML MODEL
    # ------------------------
    MODEL_PATH: str = os.getenv(
        "MODEL_PATH",
        str(BASE_DIR / "models" / "disease_model.pkl")
    )

    # ------------------------
    # SECURITY
    # ------------------------
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = get_int("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

    # ------------------------
    # CORS
    # ------------------------
    DEFAULT_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5173",
        "http://localhost:5174",
    ]

    def get_cors_origins(self) -> List[str]:
        origins = os.getenv("CORS_ORIGINS")
        if origins:
            return [o.strip() for o in origins.split(",")]
        return self.DEFAULT_CORS_ORIGINS

    # ------------------------
    # LOGGING
    # ------------------------
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # ------------------------
    # RATE LIMIT
    # ------------------------
    RATE_LIMIT_PER_MINUTE: int = get_int("RATE_LIMIT_PER_MINUTE", "60")

    # ------------------------
    # SESSION
    # ------------------------
    SESSION_TIMEOUT_MINUTES: int = get_int("SESSION_TIMEOUT_MINUTES", "60")
    MAX_SESSION_HISTORY: int = get_int("MAX_SESSION_HISTORY", "50")

    # ------------------------
    # FEATURE FLAGS
    # ------------------------
    ENABLE_STREAMING: bool = get_bool("ENABLE_STREAMING", "True")
    ENABLE_SAFETY_CHECKS: bool = get_bool("ENABLE_SAFETY_CHECKS", "True")
    ENABLE_DIAGNOSIS: bool = get_bool("ENABLE_DIAGNOSIS", "True")
    ENABLE_RECOMMENDATIONS: bool = get_bool("ENABLE_RECOMMENDATIONS", "True")

    # ------------------------
    # EMAIL (OPTIONAL)
    # ------------------------
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: Optional[int] = get_int("SMTP_PORT", "587") if os.getenv("SMTP_PORT") else None
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    EMAIL_FROM: Optional[str] = os.getenv("EMAIL_FROM")

    # ------------------------
    # MONITORING
    # ------------------------
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    ENABLE_METRICS: bool = get_bool("ENABLE_METRICS", "False")

    # ------------------------
    # FILE STORAGE
    # ------------------------
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE: int = get_int("MAX_FILE_SIZE", "10485760")  # 10MB

    # ------------------------
    # HELPERS
    # ------------------------
    def get_timestamp(self) -> str:
        return datetime.now().isoformat()

    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


# --------------------------------------------------
# INSTANCE
# --------------------------------------------------
settings = Settings()