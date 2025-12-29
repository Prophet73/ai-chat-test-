# app.py - Точка входа приложения AI Chat
# Версия 10.0 - Модульная архитектура с админкой
import sys
from pathlib import Path

# Добавляем корень проекта в path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from flask import Flask

from src.config import SECRET_KEY, DEBUG, HOST, PORT, TEMPLATES_DIR, STATIC_DIR
from src.auth import auth_bp
from src.routes import main_bp
from src.admin import admin_bp
from src.gemini_client import GEMINI_CONFIGURED
from src.rag import ALL_DOCUMENTS_METADATA


def create_app() -> Flask:
    """Фабрика приложения Flask"""
    app = Flask(
        __name__,
        template_folder=str(TEMPLATES_DIR),
        static_folder=str(STATIC_DIR)
    )
    app.secret_key = SECRET_KEY

    # Регистрация blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    return app


app = create_app()


if __name__ == '__main__':
    print("=" * 50)
    print("  AI Chat - Severin Hub Assistant v10.0")
    print("=" * 50)

    status = []
    if not GEMINI_CONFIGURED:
        status.append("  [!] Gemini API не настроен")
    if not ALL_DOCUMENTS_METADATA:
        status.append("  [!] Манифест документов не загружен")

    if status:
        for s in status:
            print(s)
    else:
        print("  [OK] Все компоненты готовы")

    print(f"\n  Запуск: http://{HOST}:{PORT}")
    print("=" * 50)

    app.run(host=HOST, port=PORT, debug=DEBUG)
