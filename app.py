from datetime import date, datetime
from functools import wraps

from flask import (Flask, abort, flash, redirect, render_template, request,
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


# Допустимые значения полей задачи (совпадают с CHECK-ограничениями в БД)
PRIORITIES = ('низкий', 'средний', 'высокий')
STATUSES = ('новая', 'в работе', 'выполнена')


def user_categories():
    """Категории текущего пользователя (для выпадающего списка в форме)."""
    return db.query(
        'SELECT id, name FROM categories WHERE user_id = %s ORDER BY name',
        (session['user_id'],),
    )


def parse_task_form():
    """Разбирает и проверяет форму задачи.

    Возвращает кортеж (данные для БД или None, сообщение об ошибке или None).
    """
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip() or None
    priority = request.form.get('priority', 'средний')
    status = request.form.get('status', 'новая')
    deadline_raw = request.form.get('deadline', '').strip()
    category_raw = request.form.get('category_id', '').strip()

    if not title or len(title) > 200:
        return None, 'Введите название задачи (до 200 символов)'
    if priority not in PRIORITIES:
        return None, 'Некорректный приоритет'
    if status not in STATUSES:
        return None, 'Некорректный статус'

    deadline = None
    if deadline_raw:
        try:
            deadline = datetime.strptime(deadline_raw, '%Y-%m-%d').date()
        except ValueError:
            return None, 'Некорректная дата дедлайна'

    category_id = None
    if category_raw:
        try:
            category_id = int(category_raw)
        except ValueError:
            return None, 'Некорректная категория'
        cat = db.query(
            'SELECT id FROM categories WHERE id = %s AND user_id = %s',
            (category_id, session['user_id']),
            fetch='one',
        )
        if cat is None:
            return None, 'Выбрана недоступная категория'

    return {
        'title': title,
        'description': description,
        'priority': priority,
        'status': status,
        'deadline': deadline,
        'category_id': category_id,
    }, None


def load_task_or_404(task_id):
    """Задача текущего пользователя или 404 (чужие задачи не видны)."""
    task = db.query(
        'SELECT * FROM tasks WHERE id = %s AND user_id = %s',
        (task_id, session['user_id']),
        fetch='one',
    )
    if task is None:
        abort(404)
    return task


def form_defaults(task=None):
    """Значения полей формы: из формы при ошибке, из задачи, иначе пустые."""
    if request.method == 'POST':
        return {
            'title': request.form.get('title', ''),
            'description': request.form.get('description', ''),
            'priority': request.form.get('priority', 'средний'),
            'status': request.form.get('status', 'новая'),
            'deadline': request.form.get('deadline', ''),
            'category_id': request.form.get('category_id', ''),
        }
    if task is None:
        return {'title': '', 'description': '', 'priority': 'средний',
                'status': 'новая', 'deadline': '', 'category_id': ''}
    return {
        'title': task['title'],
        'description': task['description'] or '',
        'priority': task['priority'],
        'status': task['status'],
        'deadline': task['deadline'].isoformat() if task['deadline'] else '',
        'category_id': str(task['category_id']) if task['category_id'] else '',
    }


@app.route('/')
@login_required
def index():
    """Главная страница — список своих задач.

    Сортировка по дедлайну: сначала ближайшие, без дедлайна — в конце.
    """
    tasks = db.query(
        '''
        SELECT tasks.*, categories.name AS category_name
        FROM tasks
        LEFT JOIN categories ON categories.id = tasks.category_id
        WHERE tasks.user_id = %s
        ORDER BY tasks.deadline ASC NULLS LAST, tasks.id DESC
        ''',
        (session['user_id'],),
    )
    return render_template('index.html', tasks=tasks, today=date.today())


@app.route('/tasks/new', methods=['GET', 'POST'])
@login_required
def task_create():
    """Создание новой задачи."""
    if request.method == 'POST':
        data, error = parse_task_form()
        if error:
            flash(error, 'danger')
        else:
            db.query(
                '''
                INSERT INTO tasks (user_id, category_id, title, description,
                                   priority, deadline, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''',
                (session['user_id'], data['category_id'], data['title'],
                 data['description'], data['priority'], data['deadline'],
                 data['status']),
                fetch='none',
            )
            flash('Задача добавлена', 'success')
            return redirect(url_for('index'))

    return render_template(
        'task_form.html',
        page_title='Новая задача',
        action_url=url_for('task_create'),
        categories=user_categories(),
        form=form_defaults(),
    )


@app.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def task_edit(task_id):
    """Редактирование своей задачи."""
    task = load_task_or_404(task_id)
    if request.method == 'POST':
        data, error = parse_task_form()
        if error:
            flash(error, 'danger')
        else:
            db.query(
                '''
                UPDATE tasks
                SET category_id = %s, title = %s, description = %s,
                    priority = %s, deadline = %s, status = %s
                WHERE id = %s
                ''',
                (data['category_id'], data['title'], data['description'],
                 data['priority'], data['deadline'], data['status'], task_id),
                fetch='none',
            )
            flash('Изменения сохранены', 'success')
            return redirect(url_for('index'))

    return render_template(
        'task_form.html',
        page_title='Редактирование задачи',
        action_url=url_for('task_edit', task_id=task_id),
        categories=user_categories(),
        form=form_defaults(task),
    )


@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def task_delete(task_id):
    """Удаление своей задачи (POST + подтверждение в браузере)."""
    load_task_or_404(task_id)
    db.query('DELETE FROM tasks WHERE id = %s', (task_id,), fetch='none')
    flash('Задача удалена', 'success')
    return redirect(url_for('index'))


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
