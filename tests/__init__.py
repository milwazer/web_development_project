# Пакет тестов проекта «Органайзер».
# Запуск из корня проекта:
#   python -m unittest discover tests -v
import os
import secrets
import sys

# чтобы import app работал независимо от того, откуда запущены тесты
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402,F401
import db  # noqa: E402

TEST_PASSWORD = 'test123'


def make_client():
    """Новый тестовый клиент Flask."""
    return app.test_client()


def post(client, url, data=None, **kwargs):
    """POST-запрос с автоматическим CSRF-токеном из сессии клиента."""
    with client.session_transaction() as s:
        if 'csrf_token' not in s:
            s['csrf_token'] = secrets.token_hex(16)
        token = s['csrf_token']
    payload = dict(data or {})
    payload['csrf_token'] = token
    return client.post(url, data=payload, **kwargs)


def register_and_login(client, email, password=TEST_PASSWORD):
    """Регистрирует пользователя и автоматически входит в аккаунт."""
    client.get('/logout')
    return post(client, '/register', data={'email': email, 'password': password,
                                           'password2': password})


def drop_user(email):
    """Удаляет тестового пользователя (его задачи и категории — каскадом)."""
    db.query('DELETE FROM users WHERE email = %s', (email,), fetch='none')
