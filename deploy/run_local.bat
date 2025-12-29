@echo off
REM run_local.bat - Запуск для локальной разработки (Windows)

echo ==========================================
echo   AI Chat - Local Development
echo ==========================================

REM Проверка виртуального окружения
if not exist "venv" (
    echo [INFO] Создание виртуального окружения...
    python -m venv venv
)

REM Активация venv
echo [INFO] Активация виртуального окружения...
call venv\Scripts\activate.bat

REM Установка зависимостей
echo [INFO] Установка зависимостей...
pip install -r requirements.txt -q

REM Проверка .env
if not exist ".env" (
    echo [WARN] Файл .env не найден, копирую из примера...
    copy deploy\.env.example .env
    echo [INFO] Отредактируйте .env и укажите ваши ключи
)

REM Установка DEV_MODE
set DEV_MODE=true
set FLASK_DEBUG=true

echo.
echo [OK] Запуск сервера разработки...
echo URL: http://localhost:5001
echo.

python src/app.py
