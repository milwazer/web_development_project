import secrets
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
        user = current_user()
        if user is None:
            flash('Сначала войдите в аккаунт', 'warning')
            return redirect(url_for('login'))
        if user['is_blocked']:
            # заблокированного разлогиниваем при первом же действии
            session.clear()
            flash('Ваш аккаунт заблокирован администратором', 'danger')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    """Декоратор: страница доступна только администратору (иначе 404)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None or user['role'] != 'admin':
            abort(404)
        return view(*args, **kwargs)
    return wrapper


@app.context_processor
def inject_template_helpers():
    """Делает current_user() и csrf_token() доступными во всех шаблонах."""
    return {'current_user': current_user, 'csrf_token': get_csrf_token}


# Допустимые значения полей задачи (совпадают с CHECK-ограничениями в БД)
PRIORITIES = ('низкий', 'средний', 'высокий')
STATUSES = ('новая', 'в работе', 'выполнена')

# Задач на одну страницу (пагинация)
PER_PAGE = 10


def get_csrf_token():
    """Токен защиты форм от CSRF, хранится в сессии пользователя."""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(16)
    return session['csrf_token']


def check_csrf():
    """Проверяет CSRF-токен POST-запроса; при ошибке — 400."""
    token = request.form.get('csrf_token', '')
    if not token or token != session.get('csrf_token'):
        abort(400, description='Неверный CSRF-токен. '
                               'Обновите страницу и попробуйте снова.')


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
        # принимаем оба формата: ДД.ММ.ГГГГ (для человека) и ГГГГ-ММ-ДД
        for fmt in ('%d.%m.%Y', '%Y-%m-%d'):
            try:
                deadline = datetime.strptime(deadline_raw, fmt).date()
                break
            except ValueError:
                continue
        if deadline is None:
            return None, 'Некорректная дата дедлайна (формат ДД.ММ.ГГГГ)'

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


def load_category_or_404(category_id):
    """Категория текущего пользователя или 404."""
    cat = db.query(
        'SELECT * FROM categories WHERE id = %s AND user_id = %s',
        (category_id, session['user_id']),
        fetch='one',
    )
    if cat is None:
        abort(404)
    return cat


def valid_category_name(name):
    """Проверка названия категории. Возвращает сообщение об ошибке или None."""
    if not name or len(name) > 50:
        return 'Введите название категории (до 50 символов)'
    if db.query('SELECT id FROM categories WHERE user_id = %s AND name = %s',
                (session['user_id'], name), fetch='one'):
        return 'Такая категория уже есть'
    return None


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
        'deadline': task['deadline'].strftime('%d.%m.%Y') if task['deadline'] else '',
        'category_id': str(task['category_id']) if task['category_id'] else '',
    }


@app.route('/')
@login_required
def index():
    """Главная страница — список своих задач с поиском и фильтрами.

    Параметры запроса: q (подстрока названия), category (id),
    status (статус), overdue=1 (только просроченные).
    """
    search = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()
    overdue = request.args.get('overdue', '') == '1'

    try:
        page = int(request.args.get('page', '1'))
    except ValueError:
        page = 1

    # условия собираются динамически, но значения всегда передаются
    # параметрами — защита от SQL-инъекций сохраняется
    where_sql = ' WHERE tasks.user_id = %s'
    params = [session['user_id']]

    if search:
        where_sql += ' AND tasks.title ILIKE %s'
        params.append('%' + search + '%')
    if category:
        try:
            params.append(int(category))
            where_sql += ' AND tasks.category_id = %s'
        except ValueError:
            pass  # мусор в параметре — просто игнорируем фильтр
    if status:
        where_sql += ' AND tasks.status = %s'
        params.append(status)
    if overdue:
        where_sql += " AND tasks.deadline < CURRENT_DATE AND tasks.status != 'выполнена'"

    # всего задач с учётом фильтров (для числа страниц)
    total_count = db.query(
        'SELECT COUNT(*) AS n FROM tasks' + where_sql,
        tuple(params), fetch='one',
    )['n']
    total_pages = max(1, (total_count + PER_PAGE - 1) // PER_PAGE)
    page = min(max(page, 1), total_pages)

    tasks = db.query(
        '''
        SELECT tasks.*, categories.name AS category_name
        FROM tasks
        LEFT JOIN categories ON categories.id = tasks.category_id
        ''' + where_sql + '''
        ORDER BY tasks.deadline ASC NULLS LAST, tasks.id DESC
        LIMIT %s OFFSET %s
        ''',
        tuple(params) + (PER_PAGE, (page - 1) * PER_PAGE),
    )
    # параметры фильтров без page — чтобы ссылки страниц их сохраняли
    args = request.args.to_dict()
    args.pop('page', None)
    return render_template('index.html', tasks=tasks, today=date.today(),
                           categories=user_categories(),
                           page=page, total_pages=total_pages,
                           total_count=total_count, args=args)


@app.route('/tasks/new', methods=['GET', 'POST'])
@login_required
def task_create():
    """Создание новой задачи."""
    if request.method == 'POST':
        check_csrf()
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
        check_csrf()
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
    check_csrf()
    load_task_or_404(task_id)
    db.query('DELETE FROM tasks WHERE id = %s', (task_id,), fetch='none')
    flash('Задача удалена', 'success')
    return redirect(url_for('index'))


@app.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    """Список категорий пользователя и добавление новой."""
    if request.method == 'POST':
        check_csrf()
        name = request.form.get('name', '').strip()
        error = valid_category_name(name)
        if error:
            flash(error, 'danger')
        else:
            db.query('INSERT INTO categories (user_id, name) VALUES (%s, %s)',
                     (session['user_id'], name), fetch='none')
            flash('Категория добавлена', 'success')
        return redirect(url_for('categories'))

    cats = db.query(
        '''
        SELECT categories.id, categories.name, COUNT(tasks.id) AS task_count
        FROM categories
        LEFT JOIN tasks ON tasks.category_id = categories.id
        WHERE categories.user_id = %s
        GROUP BY categories.id, categories.name
        ORDER BY categories.name
        ''',
        (session['user_id'],),
    )
    return render_template('categories.html', categories=cats)


@app.route('/categories/<int:category_id>/rename', methods=['POST'])
@login_required
def category_rename(category_id):
    """Переименование своей категории."""
    load_category_or_404(category_id)
    check_csrf()
    name = request.form.get('name', '').strip()
    error = valid_category_name(name)
    if error:
        flash(error, 'danger')
    else:
        db.query('UPDATE categories SET name = %s WHERE id = %s',
                 (name, category_id), fetch='none')
        flash('Категория переименована', 'success')
    return redirect(url_for('categories'))


@app.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def category_delete(category_id):
    """Удаление своей категории. Её задачи остаются без категории (SET NULL)."""
    load_category_or_404(category_id)
    check_csrf()
    db.query('DELETE FROM categories WHERE id = %s', (category_id,), fetch='none')
    flash('Категория удалена. Её задачи остались без категории.', 'success')
    return redirect(url_for('categories'))


@app.route('/profile')
@login_required
def profile():
    """Профиль: данные аккаунта и статистика задач (ФР-13)."""
    user = current_user()
    stats = db.query(
        '''
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE status = 'выполнена') AS done,
               COUNT(*) FILTER (WHERE deadline < CURRENT_DATE
                                AND status != 'выполнена') AS overdue
        FROM tasks
        WHERE user_id = %s
        ''',
        (session['user_id'],),
        fetch='one',
    )
    return render_template('profile.html', user=user, stats=stats)


@app.route('/profile/password', methods=['POST'])
@login_required
def change_password():
    """Смена пароля с вводом старого (ФР-14)."""
    check_csrf()
    old = request.form.get('old_password', '')
    new = request.form.get('new_password', '')
    new2 = request.form.get('new_password2', '')

    user = db.query('SELECT password_hash FROM users WHERE id = %s',
                    (session['user_id'],), fetch='one')
    if not check_password_hash(user['password_hash'], old):
        flash('Текущий пароль указан неверно', 'danger')
    elif len(new) < 6:
        flash('Новый пароль должен быть не короче 6 символов', 'danger')
    elif new != new2:
        flash('Новые пароли не совпадают', 'danger')
    else:
        db.query('UPDATE users SET password_hash = %s WHERE id = %s',
                 (generate_password_hash(new), session['user_id']), fetch='none')
        flash('Пароль изменён', 'success')
    return redirect(url_for('profile'))


@app.route('/admin')
@admin_required
def admin_panel():
    """Панель администратора: список пользователей с поиском по email."""
    search = request.args.get('q', '').strip()
    sql = '''
        SELECT users.id, users.email, users.role, users.is_blocked,
               COUNT(tasks.id) AS task_count
        FROM users
        LEFT JOIN tasks ON tasks.user_id = users.id
        WHERE 1 = 1
    '''
    params = []
    if search:
        sql += ' AND users.email ILIKE %s'
        params.append('%' + search + '%')
    sql += '''
        GROUP BY users.id, users.email, users.role, users.is_blocked
        ORDER BY users.id
    '''
    users = db.query(sql, tuple(params))
    return render_template('admin.html', users=users, search=search)


@app.route('/admin/<int:user_id>/block', methods=['POST'])
@admin_required
def admin_block(user_id):
    """Блокировка пользователя (самого себя блокировать нельзя)."""
    if user_id == session['user_id']:
        flash('Нельзя заблокировать самого себя', 'danger')
        return redirect(url_for('admin_panel'))
    check_csrf()
    db.query('UPDATE users SET is_blocked = TRUE WHERE id = %s', (user_id,),
             fetch='none')
    flash('Пользователь заблокирован', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/<int:user_id>/unblock', methods=['POST'])
@admin_required
def admin_unblock(user_id):
    """Разблокировка пользователя."""
    check_csrf()
    db.query('UPDATE users SET is_blocked = FALSE WHERE id = %s', (user_id,),
             fetch='none')
    flash('Пользователь разблокирован', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete(user_id):
    """Удаление пользователя вместе с задачами и категориями (ON DELETE CASCADE)."""
    if user_id == session['user_id']:
        flash('Нельзя удалить самого себя', 'danger')
        return redirect(url_for('admin_panel'))
    check_csrf()
    db.query('DELETE FROM users WHERE id = %s', (user_id,), fetch='none')
    flash('Пользователь удалён вместе с его данными', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя."""
    if request.method == 'POST':
        check_csrf()
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
        check_csrf()
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
