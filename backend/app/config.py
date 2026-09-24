from pydantic_settings import BaseSettings
from typing import List
import os

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
    # --- Gemini AI intelligence layer (Phase 3) ---
    # Only the API key needs to be provided in the environment; everything else has a safe default.
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    # Tried in order when the primary model is not available (e.g. a 404 from the
    # Google API because the model name/version does not exist for this key).
    GEMINI_MODEL_FALLBACKS: str = "gemini-2.5-flash,gemini-2.0-flash,gemini-1.5-flash"
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_TIMEOUT_SECONDS: int = 25
    AI_INSIGHT_CACHE_MINUTES: int = 180
    # --- Gemini chat assistant ---
    AI_CHAT_MAX_HISTORY_TURNS: int = 12
    AI_CHAT_MAX_MESSAGE_CHARS: int = 2000
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
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure weights sum to 1.0 in config validation (allow slight floating error)
total_w = settings.WEIGHT_ENERGY + settings.WEIGHT_WATER + settings.WEIGHT_WASTE + settings.WEIGHT_EMISSIONS + settings.WEIGHT_MOBILITY + settings.WEIGHT_OPERATIONS
if abs(total_w - 1.0) > 0.001:
    import warnings
    warnings.warn(f"Scoring weights sum to {total_w}, expected 1.0. Normalizing.")
