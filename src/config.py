# config.py - Конфигурация приложения
import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка .env из корня проекта
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# --- Пути ---
STATIC_DIR = BASE_DIR / 'static'
TEMPLATES_DIR = BASE_DIR / 'templates'
TEXT_INSTRUCTIONS_DIR = STATIC_DIR / 'text_instructions'
PDF_DATA_DIR = STATIC_DIR / 'data'
VECTOR_STORE_DIR = STATIC_DIR / 'vector_store'
MANIFEST_PATH = BASE_DIR / 'documents_manifest.json'

# --- Flask ---
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "change-me-in-production")
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
PORT = int(os.environ.get("FLASK_PORT", 5001))

# --- Gemini AI ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.5-flash")
EMBEDDING_MODEL = "text-embedding-004"

# --- OAuth2 (Hub) ---
HUB_BASE_URL = os.environ.get("HUB_BASE_URL", "https://ai-hub.svrd.ru")
HUB_CLIENT_ID = os.environ.get("HUB_CLIENT_ID", "")
HUB_CLIENT_SECRET = os.environ.get("HUB_CLIENT_SECRET", "")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5001")

# OAuth2 endpoints
HUB_AUTHORIZE_URL = f"{HUB_BASE_URL}/oauth/authorize"
HUB_TOKEN_URL = f"{HUB_BASE_URL}/oauth/token"
HUB_USERINFO_URL = f"{HUB_BASE_URL}/oauth/userinfo"
HUB_REDIRECT_URI = f"{APP_BASE_URL}/auth/callback"

# Hub Admin API (для получения данных пользователей)
HUB_API_URL = f"{HUB_BASE_URL}/api"

# Режим разработки
DEV_MODE = os.environ.get("DEV_MODE", "false").lower() == "true"
