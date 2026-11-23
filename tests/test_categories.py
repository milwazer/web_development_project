"""Тесты категорий (CRUD и SET NULL при удалении)."""
import unittest

import db

from tests import post, make_client, register_and_login, drop_user, TEST_PASSWORD

TEST_EMAIL = 'categories-unittest@example.com'


class CategoryTests(unittest.TestCase):
    def setUp(self):
        self.c = make_client()
        drop_user(TEST_EMAIL)
        register_and_login(self.c, TEST_EMAIL)
        self.user_id = db.query('SELECT id FROM users WHERE email = %s',
                                (TEST_EMAIL,), fetch='one')['id']

    def tearDown(self):
        # задачи и категории удалятся каскадом вместе с пользователем
        drop_user(TEST_EMAIL)
        drop_user('categories-unittest-2@example.com')

    def cat_id(self, name):
        row = db.query(
            'SELECT id FROM categories WHERE name = %s AND user_id = %s',
            (name, self.user_id), fetch='one')
        return row['id'] if row else None

    def test_create_and_duplicate(self):
        """Категория создаётся, повторная — отклоняется."""
        r = post(self.c, '/categories', data={'name': 'Работа'}, follow_redirects=True)
        self.assertIn('Категория добавлена', r.get_data(as_text=True))
        r = post(self.c, '/categories', data={'name': 'Работа'}, follow_redirects=True)
        self.assertIn('уже есть', r.get_data(as_text=True))

    def test_empty_name_rejected(self):
        """Пустое название отклоняется."""
        r = post(self.c, '/categories', data={'name': '   '}, follow_redirects=True)
        self.assertIn('Введите название', r.get_data(as_text=True))

    def test_rename(self):
        """Переименование категории сохраняется."""
        post(self.c, '/categories', data={'name': 'Старое имя'})
        cat_id = self.cat_id('Старое имя')
        r = post(self.c, f'/categories/{cat_id}/rename', data={'name': 'Новое имя'},
                        follow_redirects=True)
        self.assertIn('Категория переименована', r.get_data(as_text=True))
        self.assertIsNone(self.cat_id('Старое имя'))
        self.assertIsNotNone(self.cat_id('Новое имя'))

    def test_delete_sets_task_category_null(self):
        """При удалении категории её задачи сохраняются без категории (ФР-9)."""
        post(self.c, '/categories', data={'name': 'Временная'})
        cat_id = self.cat_id('Временная')
        post(self.c, '/tasks/new', data={'title': 'Чья-то задача',
                                        'priority': 'низкий', 'status': 'новая',
                                        'category_id': cat_id})
        r = post(self.c, f'/categories/{cat_id}/delete', follow_redirects=True)
        self.assertIn('Категория удалена', r.get_data(as_text=True))
        task = db.query('SELECT category_id FROM tasks WHERE title = %s',
                        ('Чья-то задача',), fetch='one')
        self.assertIsNotNone(task)
        self.assertIsNone(task['category_id'])

    def test_foreign_category_returns_404(self):
        """Категории другого пользователя недоступны."""
        post(self.c, '/categories', data={'name': 'Моя'})
        cat_id = self.cat_id('Моя')
        other = make_client()
        register_and_login(other, 'categories-unittest-2@example.com')
        self.assertEqual(
            post(other, f'/categories/{cat_id}/rename', data={'name': 'x'}).status_code,
            404)


if __name__ == '__main__':
    unittest.main()
