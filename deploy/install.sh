#!/bin/bash
# install.sh - Полная установка AI Chat с нуля
set -e

echo "=========================================="
echo "  AI Chat - Автоматическая установка"
echo "=========================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция логирования
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Проверка root
if [ "$EUID" -eq 0 ]; then
    log_error "Не запускайте от root! Используйте обычного пользователя с sudo."
    exit 1
fi

# Определение директории
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
cd "$APP_DIR"

log_info "Рабочая директория: $APP_DIR"

# ============================================
# 1. Установка Docker
# ============================================
install_docker() {
    if command -v docker &> /dev/null; then
        log_info "Docker уже установлен: $(docker --version)"
        return 0
    fi

    log_info "Установка Docker..."

    # Удаление старых версий
    sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

    # Установка зависимостей
    sudo apt-get update
    sudo apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    # Добавление GPG ключа Docker
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # Добавление репозитория
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Установка Docker
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Добавление пользователя в группу docker
    sudo usermod -aG docker $USER

    log_info "Docker установлен. Требуется перелогиниться для применения прав группы docker."
}

# ============================================
# 2. Установка Docker Compose (если нет плагина)
# ============================================
install_docker_compose() {
    if docker compose version &> /dev/null; then
        log_info "Docker Compose уже установлен: $(docker compose version)"
        return 0
    fi

    if command -v docker-compose &> /dev/null; then
        log_info "Docker Compose (standalone) уже установлен"
        return 0
    fi

    log_info "Установка Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose

    log_info "Docker Compose установлен"
}

# ============================================
# 3. Проверка .env файла
# ============================================
check_env() {
    if [ ! -f ".env" ]; then
        log_warn "Файл .env не найден!"
        log_info "Создайте .env файл со следующим содержимым:"
        echo ""
        echo "=========================================="
        cat deploy/.env.example
        echo "=========================================="
        echo ""
        log_error "После создания .env запустите скрипт снова."
        exit 1
    fi

    # Проверка обязательных переменных
    source .env

    if [ -z "$HUB_CLIENT_ID" ] || [ "$HUB_CLIENT_ID" == "" ]; then
        log_warn "HUB_CLIENT_ID не заполнен в .env"
        log_info "Зарегистрируйте приложение в Hub Admin и добавьте credentials"
    fi

    log_info "Файл .env найден"
}

# ============================================
# 4. Сборка и запуск
# ============================================
build_and_run() {
    log_info "Сборка Docker образа..."

    # Используем docker compose (новый) или docker-compose (старый)
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi

    # Остановка если запущено
    $COMPOSE_CMD down 2>/dev/null || true

    # Сборка
    $COMPOSE_CMD build

    # Запуск
    log_info "Запуск контейнера..."
    $COMPOSE_CMD up -d

    # Ждём запуска
    sleep 3

    # Проверка
    if $COMPOSE_CMD ps | grep -q "Up"; then
        log_info "Контейнер запущен успешно!"
    else
        log_error "Ошибка запуска контейнера"
        $COMPOSE_CMD logs
        exit 1
    fi
}

# ============================================
# 5. Проверка работы
# ============================================
verify() {
    log_info "Проверка работы приложения..."

    sleep 2

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/ 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" == "302" ] || [ "$HTTP_CODE" == "200" ]; then
        log_info "Приложение отвечает (HTTP $HTTP_CODE)"
    else
        log_warn "Приложение не отвечает (HTTP $HTTP_CODE)"
        log_info "Проверьте логи: docker compose logs -f"
    fi
}

# ============================================
# Основной процесс
# ============================================
main() {
    log_info "Начало установки..."

    # Обновление системы
    log_info "Обновление списка пакетов..."
    sudo apt-get update -qq

    # Установка Docker
    install_docker

    # Установка Docker Compose
    install_docker_compose

    # Проверка .env
    check_env

    # Сборка и запуск
    build_and_run

    # Проверка
    verify

    echo ""
    echo "=========================================="
    echo -e "${GREEN}  Установка завершена!${NC}"
    echo "=========================================="
    echo ""
    echo "  URL: http://localhost:5001"
    echo "  Логи: docker compose logs -f ai-chat"
    echo ""
    echo "  Следующие шаги:"
    echo "  1. Настройте nginx proxy на ai-chat.svrd.ru -> localhost:5001"
    echo "  2. Зарегистрируйте приложение в Hub Admin"
    echo "  3. Добавьте HUB_CLIENT_ID и HUB_CLIENT_SECRET в .env"
    echo "  4. Перезапустите: docker compose restart"
    echo ""
}

# Запуск
main "$@"
