# auth.py - OAuth2 авторизация через Hub
import secrets
import traceback
from functools import wraps

import requests
from flask import Blueprint, session, redirect, url_for, request, jsonify

from src.config import (
    DEV_MODE, HUB_AUTHORIZE_URL, HUB_TOKEN_URL, HUB_USERINFO_URL,
    HUB_CLIENT_ID, HUB_CLIENT_SECRET, HUB_REDIRECT_URI
)

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    """Декоратор - требует авторизацию"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if DEV_MODE:
            if 'user' not in session:
                session['user'] = {
                    'id': 'dev-user',
                    'email': 'dev@localhost',
                    'display_name': 'Dev User',
                    'is_admin': True
                }
            return f(*args, **kwargs)

        if 'access_token' not in session or 'user' not in session:
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Декоратор - требует права администратора"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or not user.get('is_admin'):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Получить текущего пользователя"""
    return session.get('user')


def get_access_token():
    """Получить access token для API запросов к Hub"""
    return session.get('access_token')


@auth_bp.route('/login')
def login():
    """Редирект на Hub для авторизации"""
    if DEV_MODE:
        session['user'] = {
            'id': 'dev-user',
            'email': 'dev@localhost',
            'display_name': 'Dev User',
            'is_admin': True
        }
        return redirect(url_for('main.index'))

    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state

    auth_url = (
        f"{HUB_AUTHORIZE_URL}?"
        f"response_type=code&"
        f"client_id={HUB_CLIENT_ID}&"
        f"redirect_uri={HUB_REDIRECT_URI}&"
        f"scope=openid+profile+email&"
        f"state={state}"
    )
    return redirect(auth_url)


@auth_bp.route('/auth/callback')
def callback():
    """Callback после авторизации в Hub"""
    error = request.args.get('error')
    if error:
        error_desc = request.args.get('error_description', 'Неизвестная ошибка')
        return f"Ошибка авторизации: {error} - {error_desc}", 400

    code = request.args.get('code')
    state = request.args.get('state')

    if not state or state != session.get('oauth_state'):
        return "Ошибка: неверный state", 400

    if not code:
        return "Ошибка: отсутствует authorization code", 400

    try:
        # Обмен кода на токены
        token_response = requests.post(
            HUB_TOKEN_URL,
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': HUB_REDIRECT_URI,
                'client_id': HUB_CLIENT_ID,
                'client_secret': HUB_CLIENT_SECRET,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10
        )

        if token_response.status_code != 200:
            print(f"Token error: {token_response.status_code} - {token_response.text}")
            return f"Ошибка получения токена: {token_response.status_code}", 400

        tokens = token_response.json()
        access_token = tokens.get('access_token')

        if not access_token:
            return "Ошибка: токен не получен", 400

        # Получение информации о пользователе
        userinfo_response = requests.get(
            HUB_USERINFO_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10
        )

        if userinfo_response.status_code != 200:
            print(f"Userinfo error: {userinfo_response.status_code}")
            return f"Ошибка получения данных пользователя", 400

        user_info = userinfo_response.json()

        # Сохранение в сессию
        session['access_token'] = access_token
        session['refresh_token'] = tokens.get('refresh_token')
        session['user'] = {
            'id': user_info.get('sub') or user_info.get('id'),
            'email': user_info.get('email'),
            'display_name': user_info.get('name') or user_info.get('display_name'),
            'department': user_info.get('department'),
            'job_title': user_info.get('job_title'),
            'is_admin': user_info.get('is_admin', False),
        }

        session.pop('oauth_state', None)
        next_url = session.pop('next_url', None)
        return redirect(next_url or url_for('main.index'))

    except requests.RequestException as e:
        print(f"OAuth error: {e}")
        traceback.print_exc()
        return f"Ошибка связи с Hub: {e}", 500


@auth_bp.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/api/me')
@login_required
def me():
    """API - данные текущего пользователя"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify(user)
