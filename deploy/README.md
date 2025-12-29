# AI Chat - Инструкция по деплою

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/Prophet73/ai-chat-test-.git ai-chat
cd ai-chat
```

### 2. Настройка конфигурации

```bash
cp deploy/.env.example .env
nano .env
```

Заполните обязательные поля:

```env
# Flask
FLASK_SECRET_KEY="сгенерируйте-случайную-строку-32-символа"

# Google Gemini API
GEMINI_API_KEY="ваш-ключ-gemini"

# OAuth2 (получить в Hub Admin -> Applications)
HUB_BASE_URL="https://ai-hub.svrd.ru"
HUB_CLIENT_ID="client_id_из_хаба"
HUB_CLIENT_SECRET="client_secret_из_хаба"

# URL этого приложения (где будет развернут ai-chat)
APP_BASE_URL="https://ai-chat.your-domain.ru"

# Отключить dev mode для продакшена!
DEV_MODE=false
```

### 3. Регистрация приложения в Hub

1. Зайдите в Hub Admin: https://ai-hub.svrd.ru/admin
2. Перейдите в **Applications** → **Create**
3. Заполните:
   - **Name:** AI Chat
   - **Redirect URI:** `https://ai-chat.your-domain.ru/auth/callback`
4. Скопируйте `client_id` и `client_secret` в `.env`

---

## Варианты деплоя

### Вариант A: Docker (рекомендуется)

```bash
# Запуск с docker-compose
docker-compose up -d

# Или только приложение без nginx
docker-compose up -d ai-chat
```

Приложение будет доступно на порту `5001`.

### Вариант B: Скрипт деплоя

```bash
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

Скрипт автоматически:
- Создаст виртуальное окружение
- Установит зависимости
- Запустит через gunicorn на порту 5001

### Вариант C: Systemd сервис

```bash
# Создание сервиса
sudo nano /etc/systemd/system/ai-chat.service
```

```ini
[Unit]
Description=AI Chat Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ai-chat
Environment=PATH=/opt/ai-chat/venv/bin
ExecStart=/opt/ai-chat/venv/bin/gunicorn --workers 4 --bind 0.0.0.0:5001 src.app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-chat
sudo systemctl start ai-chat
```

---

## Настройка Nginx (reverse proxy)

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/ai-chat
sudo ln -s /etc/nginx/sites-available/ai-chat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Не забудьте:
1. Изменить `server_name` в nginx.conf на ваш домен
2. Настроить SSL сертификаты (Let's Encrypt или свои)

### SSL с Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d ai-chat.your-domain.ru
```

---

## Проверка работы

```bash
# Статус сервиса
sudo systemctl status ai-chat

# Логи
sudo journalctl -u ai-chat -f

# Или для Docker
docker-compose logs -f ai-chat
```

---

## Локальная разработка

### Windows
```cmd
deploy\run_local.bat
```

### Linux/Mac
```bash
chmod +x deploy/run_local.sh
./deploy/run_local.sh
```

В режиме разработки (`DEV_MODE=true`) авторизация пропускается.

---

## Структура проекта

```
ai-chat/
├── src/
│   ├── app.py           # Точка входа Flask
│   ├── config.py        # Конфигурация из .env
│   ├── auth.py          # OAuth2 авторизация с Hub
│   ├── admin.py         # Админ-панель
│   ├── routes.py        # Основные роуты чата
│   ├── gemini_client.py # Клиент Google Gemini
│   ├── rag.py           # RAG система
│   └── prompts.py       # Промпты для AI
├── templates/           # HTML шаблоны
├── static/              # CSS, JS, изображения
├── documents/           # База знаний (документы)
├── deploy/
│   ├── deploy.sh        # Скрипт деплоя
│   ├── run_local.sh     # Локальный запуск (Linux)
│   ├── run_local.bat    # Локальный запуск (Windows)
│   ├── nginx.conf       # Конфиг Nginx
│   └── .env.example     # Пример конфигурации
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Troubleshooting

### Ошибка подключения к Hub
- Проверьте доступность `ai-hub.svrd.ru` с сервера
- Проверьте правильность `HUB_CLIENT_ID` и `HUB_CLIENT_SECRET`
- Убедитесь что `APP_BASE_URL` совпадает с Redirect URI в Hub

### 502 Bad Gateway
- Проверьте что ai-chat сервис запущен: `systemctl status ai-chat`
- Проверьте порт: `netstat -tlnp | grep 5001`

### OAuth callback error
- Проверьте что Redirect URI в Hub точно совпадает с `APP_BASE_URL/auth/callback`
