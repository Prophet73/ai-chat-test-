# admin.py - Админ-панель с данными из Hub
import traceback
from datetime import datetime

import requests
from flask import Blueprint, render_template, jsonify, session

from src.config import HUB_API_URL, DEV_MODE
from src.auth import admin_required, get_current_user, get_access_token

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def hub_api_request(endpoint: str, method: str = 'GET', data: dict = None) -> dict:
    """Выполнить запрос к Hub API"""
    access_token = get_access_token()

    if DEV_MODE:
        # В режиме разработки возвращаем моковые данные
        return get_mock_data(endpoint)

    if not access_token:
        return {'error': 'No access token', 'status': 401}

    try:
        url = f"{HUB_API_URL}/{endpoint}"
        headers = {'Authorization': f'Bearer {access_token}'}

        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            return {'error': 'Unsupported method'}

        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f'Hub API error: {response.status_code}', 'status': response.status_code}

    except requests.RequestException as e:
        print(f"Hub API error: {e}")
        traceback.print_exc()
        return {'error': str(e)}


def get_mock_data(endpoint: str) -> dict:
    """Моковые данные для режима разработки"""
    if 'users' in endpoint:
        return {
            'users': [
                {
                    'id': '1',
                    'email': 'admin@severindevelopment.ru',
                    'display_name': 'Администратор',
                    'department': 'IT отдел',
                    'job_title': 'Системный администратор',
                    'is_admin': True,
                    'is_active': True,
                    'last_login_at': datetime.now().isoformat()
                },
                {
                    'id': '2',
                    'email': 'user1@severindevelopment.ru',
                    'display_name': 'Иванов Иван',
                    'department': 'Строительный контроль',
                    'job_title': 'Инженер СК',
                    'is_admin': False,
                    'is_active': True,
                    'last_login_at': datetime.now().isoformat()
                },
                {
                    'id': '3',
                    'email': 'user2@severindevelopment.ru',
                    'display_name': 'Петров Пётр',
                    'department': 'Проектный отдел',
                    'job_title': 'Архитектор',
                    'is_admin': False,
                    'is_active': True,
                    'last_login_at': None
                },
            ],
            'total': 3
        }
    elif 'stats' in endpoint:
        return {
            'total_users': 3,
            'active_users': 2,
            'total_sessions': 15,
            'today_logins': 5
        }
    elif 'applications' in endpoint:
        return {
            'applications': [
                {
                    'id': '1',
                    'name': 'AI Chat',
                    'client_id': 'hub_ai_chat',
                    'is_active': True,
                    'created_at': datetime.now().isoformat()
                }
            ]
        }

    return {'error': 'Unknown endpoint'}


# --- Роуты админки ---

@admin_bp.route('/')
@admin_required
def index():
    """Главная страница админки"""
    user = get_current_user()
    return render_template('admin/index.html', user=user)


@admin_bp.route('/api/users')
@admin_required
def get_users():
    """API - список пользователей из Hub"""
    search = session.get('admin_user_search', '')
    page = int(session.get('admin_user_page', 1))
    per_page = 20

    # Запрос к Hub API
    endpoint = f"admin/users?page={page}&per_page={per_page}"
    if search:
        endpoint += f"&search={search}"

    result = hub_api_request(endpoint)
    return jsonify(result)


@admin_bp.route('/api/users/<user_id>')
@admin_required
def get_user(user_id):
    """API - детали пользователя"""
    result = hub_api_request(f"admin/users/{user_id}")
    return jsonify(result)


@admin_bp.route('/api/stats')
@admin_required
def get_stats():
    """API - статистика"""
    result = hub_api_request("admin/stats")
    return jsonify(result)


@admin_bp.route('/api/applications')
@admin_required
def get_applications():
    """API - список приложений"""
    result = hub_api_request("applications")
    return jsonify(result)


@admin_bp.route('/api/audit-logs')
@admin_required
def get_audit_logs():
    """API - логи аудита"""
    result = hub_api_request("admin/audit-logs?limit=50")
    return jsonify(result)


@admin_bp.route('/api/login-history')
@admin_required
def get_login_history():
    """API - история входов"""
    result = hub_api_request("admin/login-history?limit=50")
    return jsonify(result)
