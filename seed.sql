-- ============================================================
-- Тестовые данные (seed).
-- Выполнять в базе organizer ПОСЛЕ database.sql.
-- Скрипт рассчитан на пустую базу: id совпадают с порядком вставки.
--
-- Тестовые пароли:
--   admin@example.com  / admin123  (администратор)
--   user@example.com   / user123   (обычный пользователь)
--   spam@example.com   / spam123   (заблокированный пользователь)
-- Пароли в таблице хранятся в виде хешей (werkzeug, scrypt).
-- ============================================================

INSERT INTO users (email, password_hash, role, is_blocked) VALUES
('admin@example.com', 'scrypt:32768:8:1$95aNPEW3xbNmoLd2$d47376a3e80e9c23464b3832b0b3262667add64cdace8f854b0eaba8262da63cd12209db7c30e461d8c19ee52fa3d70e6d409a39f9af59768a2fe8de234a8992', 'admin', FALSE),
('user@example.com',  'scrypt:32768:8:1$iXvC7Zdbv7sFXRi1$ea3e56616ffbc4b3a1735c381b981dd953a4edca0e956bb64c71109189dbc9c39197e49a4a6c503f3969426f7a4532153dc41c609fe1bd29f661e958edc32d4a', 'user',  FALSE),
('spam@example.com',  'scrypt:32768:8:1$cYytrnGfTsDbua31$43e11c30fb2207a27aeb4aee86c40b713e14408a8b9f45c7a25efdfc512f6e51c1299bce7562f2db8028a29f2d5d90091ee6356abc4f6d904a2b3ed755267193', 'user',  TRUE);

-- Категории пользователя user@example.com (user_id = 2)
INSERT INTO categories (user_id, name) VALUES
(2, 'Учёба'),
(2, 'Дом'),
(2, 'Работа');

-- Задачи пользователя user@example.com (user_id = 2)
-- Задача «Оплатить интернет» с дедлайном 15.11.2026 — просроченная (для демонстрации фильтра).
INSERT INTO tasks (user_id, category_id, title, description, priority, deadline, status) VALUES
(2, 1, 'Курсовая работа: сдать отчёт', 'Дописать раздел «Тестирование» и отправить руководителю', 'высокий',  '2026-11-25', 'в работе'),
(2, 2, 'Оплатить интернет',           NULL,                                                     'средний',  '2026-11-15', 'новая'),
(2, 2, 'Купить продукты',             'Хлеб, молоко, яйца',                                     'средний',  '2026-11-18', 'новая'),
(2, NULL, 'Записаться к врачу',       NULL,                                                     'низкий',   NULL,         'новая'),
(2, 3, 'Подготовить презентацию',     'Для защиты курсового проекта',                           'высокий',  '2026-11-28', 'выполнена');
