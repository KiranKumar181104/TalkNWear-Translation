from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "TalkNWear"
    DATABASE_URL: str = "mongodb://localhost:27017"
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_FOR_JWT"  # Change in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AES Key for Audio Encryption (must be 32 bytes for AES-256)
    AUDIO_ENCRYPTION_KEY: str = "32byte_long_encryption_key_12345" 
    
    # AI Model Endpoints (Optional if running locally)
    WHISPER_MODEL_PATH: str = "openai/whisper-base"
    INDIC_TRANS_PATH: str = "ai4bharat/indictrans2-en-indic-dist-200M"
    
    class Config:
        env_file = ".env"

settings = Settings()
