#!/bin/bash
# deploy.sh - Скрипт деплоя AI Chat
set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  AI Chat - Deploy Script${NC}"
echo -e "${GREEN}========================================${NC}"

# Проверка .env
if [ ! -f ".env" ]; then
    echo -e "${RED}[ERROR] Файл .env не найден!${NC}"
    echo -e "${YELLOW}Создайте .env на основе .env.example${NC}"
    exit 1
fi

# Загрузка переменных
source .env

# Проверка обязательных переменных
check_var() {
    if [ -z "${!1}" ]; then
        echo -e "${RED}[ERROR] Переменная $1 не установлена в .env${NC}"
        exit 1
    fi
}

echo -e "${YELLOW}[1/5] Проверка конфигурации...${NC}"
check_var "FLASK_SECRET_KEY"
check_var "GEMINI_API_KEY"
check_var "HUB_CLIENT_ID"
check_var "HUB_CLIENT_SECRET"
check_var "APP_BASE_URL"
echo -e "${GREEN}[OK] Конфигурация в порядке${NC}"

# Остановка старых контейнеров
echo -e "${YELLOW}[2/5] Остановка старых контейнеров...${NC}"
docker-compose down --remove-orphans 2>/dev/null || true
echo -e "${GREEN}[OK] Старые контейнеры остановлены${NC}"

# Сборка образа
echo -e "${YELLOW}[3/5] Сборка Docker образа...${NC}"
docker-compose build --no-cache
echo -e "${GREEN}[OK] Образ собран${NC}"

# Запуск контейнеров
echo -e "${YELLOW}[4/5] Запуск контейнеров...${NC}"
docker-compose up -d
echo -e "${GREEN}[OK] Контейнеры запущены${NC}"

# Проверка здоровья
echo -e "${YELLOW}[5/5] Проверка здоровья...${NC}"
sleep 5

if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}[OK] Приложение запущено успешно!${NC}"
    echo ""
    echo -e "URL: ${GREEN}${APP_BASE_URL}${NC}"
    echo -e "Логи: ${YELLOW}docker-compose logs -f${NC}"
else
    echo -e "${RED}[ERROR] Приложение не запустилось${NC}"
    echo -e "${YELLOW}Проверьте логи: docker-compose logs${NC}"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Деплой завершён успешно!${NC}"
echo -e "${GREEN}========================================${NC}"
