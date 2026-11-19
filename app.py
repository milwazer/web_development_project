from functools import wraps

from flask import (Flask, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import db

app = Flask(__name__)
# загружаем настройки из config.py (секретный ключ сессии и параметры БД)
app.config.from_object('config')


def current_user():
    """Возвращает запись текущего пользователя (по сессии) или None."""
    if 'user_id' not in session:
        return None
    return db.query(
        'SELECT id, email, role, is_blocked FROM users WHERE id = %s',
        (session['user_id'],),
        fetch='one',
    )


def login_required(view):
    """Декоратор: страница доступна только вошедшим пользователям."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            flash('Сначала войдите в аккаунт', 'warning')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapper


@app.context_processor
def inject_current_user():
    """Делает current_user() доступным во всех шаблонах (для меню)."""
    return {'current_user': current_user}


@app.route('/')
@login_required
def index():
    """Главная страница — список задач (появится на следующем этапе)."""
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        # валидация формы на сервере
        if not email or '@' not in email or len(email) > 100:
            flash('Введите корректный email (до 100 символов)', 'danger')
        elif len(password) < 6:
            flash('Пароль должен быть не короче 6 символов', 'danger')
        elif password != password2:
            flash('Пароли не совпадают', 'danger')
        elif db.query('SELECT id FROM users WHERE email = %s', (email,), fetch='one'):
            flash('Пользователь с таким email уже зарегистрирован', 'danger')
        else:
            row = db.query(
                'INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id',
                (email, generate_password_hash(password)),
                fetch='one',
            )
            session['user_id'] = row['id']
            flash('Аккаунт создан. Добро пожаловать!', 'success')
            return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Авторизация по email и паролю."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = db.query(
            'SELECT id, password_hash, is_blocked FROM users WHERE email = %s',
            (email,),
            fetch='one',
        )
        # одно сообщение на оба случая, чтобы не раскрывать наличие email в базе
        if user is None or not check_password_hash(user['password_hash'], password):
            flash('Неверный email или пароль', 'danger')
        elif user['is_blocked']:
            flash('Аккаунт заблокирован администратором', 'danger')
        else:
            session['user_id'] = user['id']
            return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Выход из аккаунта: очищаем сессию."""
    session.clear()
    flash('Вы вышли из аккаунта', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
