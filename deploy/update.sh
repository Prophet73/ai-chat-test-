#!/bin/bash
# update.sh - Обновление AI Chat из git
set -e

echo "=========================================="
echo "  AI Chat - Обновление"
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
cd "$APP_DIR"

echo "[INFO] Получение обновлений из git..."
git pull origin main

echo "[INFO] Пересборка Docker образа..."
if docker compose version &> /dev/null; then
    docker compose build
    docker compose up -d
else
    docker-compose build
    docker-compose up -d
fi

echo "[INFO] Ожидание запуска..."
sleep 3

echo "[INFO] Статус:"
docker compose ps 2>/dev/null || docker-compose ps

echo ""
echo "[OK] Обновление завершено!"
