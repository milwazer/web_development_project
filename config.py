import os

# Настройки подключения к базе данных PostgreSQL.
# Значения можно переопределить переменными окружения,
# чтобы не хранить пароль в коде, например:
#   setx DB_PASSWORD "ваш_пароль"
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', '5432'))
DB_NAME = os.environ.get('DB_NAME', 'organizer')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')

# Секретный ключ для подписи сессий
SECRET_KEY = os.environ.get('SECRET_KEY', 'organizer-secret-key-2026')
