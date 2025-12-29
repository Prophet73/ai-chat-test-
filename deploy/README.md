# AI Chat - Deploy Scripts

## Быстрый деплой

```bash
# 1. Клонировать репозиторий
cd /opt
sudo git clone https://github.com/Prophet73/ai-chat-test-.git ai-chat-test
cd ai-chat-test
sudo chown -R $USER:$USER .

# 2. Создать .env файл
nano .env
# (вставить конфигурацию, см. ниже)

# 3. Запустить установку
chmod +x deploy/install.sh
./deploy/install.sh
```

---

## Скрипты

| Скрипт | Описание |
|--------|----------|
| `install.sh` | Полная установка: Docker, сборка образа, systemd сервис |
| `update.sh` | Обновление из git и пересборка контейнера |
| `run_local.sh` | Локальный запуск для разработки (Linux/Mac) |
| `run_local.bat` | Локальный запуск для разработки (Windows) |

---

## Конфигурация .env

```env
# Flask
FLASK_SECRET_KEY="сгенерируйте-случайную-строку-32-символа"
FLASK_DEBUG=false
FLASK_HOST=0.0.0.0
FLASK_PORT=5001

# Google Gemini API
GEMINI_API_KEY="ваш-ключ-gemini"
GEMINI_MODEL_NAME="gemini-2.5-flash"

# OAuth2 Hub
HUB_BASE_URL="https://ai-hub.svrd.ru"
HUB_CLIENT_ID="получить-в-hub-admin"
HUB_CLIENT_SECRET="получить-в-hub-admin"

# URL этого приложения
APP_BASE_URL="https://ai-chat.svrd.ru"

# Режим (false для продакшена!)
DEV_MODE=false
```

---

## install.sh - Что делает

1. **Устанавливает Docker** (если не установлен)
   - Docker CE
   - Docker Compose plugin
   - Добавляет пользователя в группу docker

2. **Проверяет .env** файл
   - Если нет - показывает пример и выходит

3. **Собирает Docker образ**
   - `docker compose build`

4. **Запускает контейнер**
   - `docker compose up -d`

5. **Создаёт systemd сервис**
   - `/etc/systemd/system/ai-chat.service`
   - Включает автозапуск при старте системы

6. **Проверяет работу**
   - curl http://localhost:5001

---

## Управление сервисом

```bash
# Статус
sudo systemctl status ai-chat

# Перезапуск
sudo systemctl restart ai-chat

# Остановка
sudo systemctl stop ai-chat

# Запуск
sudo systemctl start ai-chat

# Логи Docker
docker compose logs -f

# Логи systemd
sudo journalctl -u ai-chat -f
```

---

## update.sh - Обновление

```bash
./deploy/update.sh
```

Скрипт:
1. `git pull origin main` - получает изменения
2. `docker compose build` - пересобирает образ
3. `docker compose up -d` - перезапускает контейнер

---

## Настройка внешнего Nginx

Добавить в конфиг nginx для `ai-chat.svrd.ru`:

```nginx
server {
    listen 443 ssl http2;
    server_name ai-chat.svrd.ru;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://IP_СЕРВЕРА:5001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE для стриминга чата
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400;
    }
}

server {
    listen 80;
    server_name ai-chat.svrd.ru;
    return 301 https://$host$request_uri;
}
```

---

## Регистрация в Hub

1. Открыть https://ai-hub.svrd.ru/admin
2. **Applications** → **Create**
3. Заполнить:
   - Name: `AI Chat`
   - Redirect URI: `https://ai-chat.svrd.ru/auth/callback`
4. Скопировать `client_id` и `client_secret`
5. Вставить в `.env`
6. Перезапустить: `sudo systemctl restart ai-chat`

---

## Troubleshooting

### Docker не запускается
```bash
# Проверить статус Docker
sudo systemctl status docker

# Запустить Docker
sudo systemctl start docker
```

### Ошибка прав доступа Docker
```bash
# Добавить пользователя в группу docker
sudo usermod -aG docker $USER

# Перелогиниться или выполнить
newgrp docker
```

### Приложение не отвечает
```bash
# Проверить контейнер
docker ps -a

# Посмотреть логи
docker compose logs -f
```

### Ошибка OAuth
- Проверить что `APP_BASE_URL` совпадает с Redirect URI в Hub
- Проверить `HUB_CLIENT_ID` и `HUB_CLIENT_SECRET`
- Проверить доступность `ai-hub.svrd.ru` с сервера
