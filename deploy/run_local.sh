#!/bin/bash
# run_local.sh - Запуск для локальной разработки
set -e

echo "=========================================="
echo "  AI Chat - Local Development"
echo "=========================================="

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "[INFO] Создание виртуального окружения..."
    python -m venv venv
fi

# Активация venv
echo "[INFO] Активация виртуального окружения..."
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate

# Установка зависимостей
echo "[INFO] Установка зависимостей..."
pip install -r requirements.txt -q

# Проверка .env
if [ ! -f ".env" ]; then
    echo "[WARN] Файл .env не найден, копирую из примера..."
    cp deploy/.env.example .env
    echo "[INFO] Отредактируйте .env и укажите ваши ключи"
fi

# Установка DEV_MODE
export DEV_MODE=true
export FLASK_DEBUG=true

echo ""
echo "[OK] Запуск сервера разработки..."
echo "URL: http://localhost:5001"
echo ""

python src/app.py
