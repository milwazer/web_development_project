-- ============================================================
-- База данных «Органайзер»
-- 1) Сначала создать базу (если ещё не создана):
--        CREATE DATABASE organizer;
-- 2) Затем выполнить этот скрипт в базе organizer, после него — seed.sql
-- ============================================================

-- Пользователи системы
CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(10)  NOT NULL DEFAULT 'user',
    is_blocked    BOOLEAN      NOT NULL DEFAULT FALSE,
    CONSTRAINT check_role CHECK (role IN ('user', 'admin'))
);

-- Категории задач (свои у каждого пользователя)
CREATE TABLE categories (
    id      SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name    VARCHAR(50) NOT NULL
);

-- Задачи
CREATE TABLE tasks (
    id          SERIAL PRIMARY KEY,
    user_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INT REFERENCES categories(id) ON DELETE SET NULL,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    priority    VARCHAR(10) NOT NULL DEFAULT 'средний',
    deadline    DATE,
    status      VARCHAR(10) NOT NULL DEFAULT 'новая',
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_priority CHECK (priority IN ('низкий', 'средний', 'высокий')),
    CONSTRAINT check_status   CHECK (status IN ('новая', 'в работе', 'выполнена'))
);

-- Индекс для быстрого выбора задач конкретного пользователя
CREATE INDEX tasks_user_id_idx ON tasks(user_id);
