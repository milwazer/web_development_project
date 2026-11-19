import psycopg2
from psycopg2.extras import RealDictCursor

import config


def get_connection():
    """Открывает соединение с базой данных."""
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )


def query(sql, params=(), fetch='all'):
    """Выполняет SQL-запрос с параметрами (защита от SQL-инъекций).

    fetch='all'  — вернуть список строк (словари),
    fetch='one'  — вернуть одну строку (словарь) или None,
    fetch='none' — ничего не возвращать (INSERT/UPDATE/DELETE).
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            result = None
            if fetch == 'all':
                result = cur.fetchall()
            elif fetch == 'one':
                result = cur.fetchone()
            conn.commit()
            return result
    finally:
        conn.close()
