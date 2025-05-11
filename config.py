# config.py
import os
import secrets
from dotenv import load_dotenv


class Config:
    """Uygulama için yapılandırma sınıfı"""

    # Ortam değişkenlerini yükle
    load_dotenv()

    # API Yapılandırması
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

    # Flask Session için gizli anahtar
    SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(16))

    # API Türleri
    API_TYPES = {
        "openrouter": "OpenRouter API",
        "gemini": "Gemini API"
    }

    DB_HOST = "postgres-service"
    DB_PORT = 5432
    DB_NAME = "HR2"
    DB_USERNAME = "postgres"
    DB_PASSWORD = "123456"


    # Model Yapılandırması
    AVAILABLE_MODELS = {
        # OpenRouter Modelleri
        "google/gemini-2.0-pro-exp-02-05:free": {
            "name": "google/gemini-2.0-pro-exp-02-05:free",
            "display_name": "Gemini 2.0 Pro (OpenRouter)",
            "api_type": "openrouter"
        },
        "google/gemini-2.0-flash-thinking-exp:free": {
            "name": "google/gemini-2.0-flash-thinking-exp:free",
            "display_name": "Gemini 2.0 Flash Thinking (OpenRouter)",
            "api_type": "openrouter"
        },
        "deepseek/deepseek-chat-v3-0324:free": {
            "name": "deepseek-chat-v3-0324:free",
            "display_name": "DeepSeek Chat V3 (OpenRouter)",
            "api_type": "openrouter"
        },
        # Gemini API doğrudan modelleri
        "models/gemini-2.5-pro-exp-03-25": {
            "name": "models/gemini-2.5-pro-exp-03-25",
            "display_name": "Gemini 2.5 Pro Experimental",
            "api_type": "gemini"
        },
        "models/gemini-2.0-flash": {
            "name": "models/gemini-2.0-flash",
            "display_name": "Gemini 2.0 Flash",
            "api_type": "gemini"
        },
        "models/gemini-2.0-flash-lite": {
            "name": "models/gemini-2.0-flash-lite",
            "display_name": "Gemini 2.0 Flash Lite",
            "api_type": "gemini"
        },
        "models/gemini-2.5-pro-preview-03-25": {
            "name": "models/gemini-2.5-pro-preview-03-25",
            "display_name": "Gemini 2.5 Pro Preview",
            "api_type": "gemini"
        },
        "models/gemini-1.5-pro-002": {
            "name": "models/gemini-1.5-pro-002",
            "display_name": "Gemini 1.5 Pro 002",
            "api_type": "gemini"
        },
        "models/gemini-1.5-pro-latest": {
            "name": "models/gemini-1.5-pro-latest",
            "display_name": "Gemini 1.5 Pro Latest",
            "api_type": "gemini"
        }
    }

    DEFAULT_MODEL = "models/gemini-2.0-flash"
