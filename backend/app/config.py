from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings

# backend/.env is resolved relative to this file, so the key is found no matter
# which directory uvicorn is started from. Real environment variables still win.
BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"

class Settings(BaseSettings):
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "climacred"
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    ELECTRICITY_EMISSION_FACTOR_KG_PER_KWH: float = 0.82
    WATER_COST_PER_KL_INR: float = 30.0
    DIESEL_EMISSION_FACTOR_KG_PER_LITRE: float = 2.68
    PETROL_EMISSION_FACTOR_KG_PER_LITRE: float = 2.31
    NATURAL_GAS_EMISSION_FACTOR_KG_PER_KG: float = 2.75
    CALCULATION_VERSION: str = "v1.0.0"
    # --- Gemini AI layer ---------------------------------------------------
    # GEMINI_API_KEY is read ONLY from backend/.env (or the process environment).
    # It is never sent to the browser, stored in MongoDB or returned by any API.
    GEMINI_API_KEY: str = ""
    # Optional. Leave empty to let the backend pick a model that the Gemini API
    # itself reports as available for this key (models.list -> supportedGenerationMethods
    # contains "generateContent") AND that passes a real generateContent probe.
    # If you set a model, it is verified the same way before it is ever used;
    # an unavailable model is reported by GET /api/ai/status instead of being called blindly.
    # GEMINI_MODEL: configured default model is gemini-3.8-flash
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com/v1beta"
    # Thinking models (Gemini 2.5 / 3.x) can take a while on large prompts.
    GEMINI_TIMEOUT_SECONDS: int = 60
    # GET /api/ai/status performs a real (tiny) Gemini request; results are cached briefly.
    GEMINI_STATUS_CACHE_SECONDS: int = 300
    GEMINI_STATUS_ERROR_CACHE_SECONDS: int = 30
    AI_INSIGHT_CACHE_MINUTES: int = 180
    # --- Gemini chat assistant ---
    AI_CHAT_MAX_HISTORY_TURNS: int = 12
    AI_CHAT_MAX_MESSAGE_CHARS: int = 2000
    # --- Data hygiene -------------------------------------------------------
    # Older builds auto-inserted an "ABC Textile" demo business into MongoDB.
    # On startup, documents that match that exact legacy signature are removed
    # (never user-created data). See app/database/legacy_demo.py.
    PURGE_LEGACY_DEMO_DATA: bool = True
    # Scoring weights configurable
    WEIGHT_ENERGY: float = 0.20
    WEIGHT_WATER: float = 0.20
    WEIGHT_WASTE: float = 0.15
    WEIGHT_EMISSIONS: float = 0.20
    WEIGHT_MOBILITY: float = 0.10
    WEIGHT_OPERATIONS: float = 0.15

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ORIGINS:
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure weights sum to 1.0 in config validation (allow slight floating error)
total_w = settings.WEIGHT_ENERGY + settings.WEIGHT_WATER + settings.WEIGHT_WASTE + settings.WEIGHT_EMISSIONS + settings.WEIGHT_MOBILITY + settings.WEIGHT_OPERATIONS
if abs(total_w - 1.0) > 0.001:
    import warnings
    warnings.warn(f"Scoring weights sum to {total_w}, expected 1.0. Normalizing.")
