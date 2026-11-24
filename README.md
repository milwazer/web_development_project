# Органайзер — курсовой проект

Веб-приложение для учёта личных задач: задачи с категориями, приоритетами и дедлайнами,
поиск, фильтры и пагинация, роли пользователя и администратора.

## Технологии

- Python 3 + Flask
- PostgreSQL
- Jinja2, werkzeug, psycopg2
- Bootstrap 5

## Запуск

1. Установить [Python 3.10+](https://www.python.org/downloads/) (галочка *Add to PATH*)
   и [PostgreSQL](https://www.postgresql.org/download/windows/), запомнить пароль пользователя `postgres`.
2. Скачать проект и установить зависимости:
   ```bash
   git clone https://github.com/milwazer/web_development_project.git
   cd web_development_project
   pip install -r requirements.txt
   ```
3. Создать базу данных (в psql или pgAdmin):
   ```sql
   CREATE DATABASE organizer;
   ```
4. Выполнить скрипты из папки проекта:
   ```bash
   psql -U postgres -d organizer -f database.sql
   psql -U postgres -d organizer -f seed.sql
   ```
5. Задать пароль от PostgreSQL (после команды открыть новую консоль):
   ```bash
   setx DB_PASSWORD "ваш_пароль"
   ```
6. Запустить приложение и открыть http://127.0.0.1:5000:
   ```bash
   python app.py
   ```

Тестовые аккаунты (создаются скриптом `seed.sql`):
`admin@example.com` / `admin123` — администратор,
`user@example.com` / `user123` — пользователь.
