"""Тесты CRUD задач и проверки прав доступа."""
import unittest

import db

from tests import make_client, register_and_login, drop_user, TEST_PASSWORD

TEST_EMAIL = 'tasks-unittest@example.com'


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.c = make_client()
        drop_user(TEST_EMAIL)
        register_and_login(self.c, TEST_EMAIL)

    def tearDown(self):
        drop_user(TEST_EMAIL)
        drop_user('tasks-unittest-2@example.com')

    def create_task(self, title='Тестовая задача', **overrides):
        data = {'title': title, 'description': '', 'priority': 'средний',
                'status': 'новая', 'deadline': '', 'category_id': ''}
        data.update(overrides)
        return self.c.post('/tasks/new', data=data)

    def task_id_by_title(self, title):
        row = db.query('SELECT id FROM tasks WHERE title = %s', (title,),
                       fetch='one')
        return row['id'] if row else None

    def test_create_and_list(self):
        """Созданная задача появляется в списке."""
        r = self.create_task()
        self.assertEqual(r.status_code, 302)
        self.assertIn('Тестовая задача', self.c.get('/').get_data(as_text=True))

    def test_empty_title_rejected(self):
        """Задача без названия не сохраняется."""
        r = self.create_task(title='   ', follow_redirects=True)
        self.assertIn('Введите название', r.get_data(as_text=True))

    def test_bad_deadline_rejected(self):
        """Некорректная дата дедлайна отклоняется."""
        r = self.create_task(title='x', deadline='не-дата', follow_redirects=True)
        self.assertIn('Некорректная дата', r.get_data(as_text=True))

    def test_foreign_category_rejected(self):
        """Чужая категория не может быть подставлена в форму."""
        r = self.create_task(title='x', category_id='999', follow_redirects=True)
        self.assertIn('недоступная категория', r.get_data(as_text=True))

    def test_edit_updates_status(self):
        """Редактирование меняет поля задачи в БД."""
        self.create_task()
        task_id = self.task_id_by_title('Тестовая задача')
        r = self.c.post(f'/tasks/{task_id}/edit', data={
            'title': 'Тестовая задача', 'description': '',
            'priority': 'высокий', 'status': 'выполнена',
            'deadline': '2026-12-15', 'category_id': '',
        })
        self.assertEqual(r.status_code, 302)
        row = db.query('SELECT priority, status, deadline FROM tasks WHERE id = %s',
                       (task_id,), fetch='one')
        self.assertEqual(row['status'], 'выполнена')
        self.assertEqual(row['priority'], 'высокий')

    def test_delete_removes_task(self):
        """Удалённой задачи нет в базе."""
        self.create_task(title='Задача на удаление')
        task_id = self.task_id_by_title('Задача на удаление')
        r = self.c.post(f'/tasks/{task_id}/delete')
        self.assertEqual(r.status_code, 302)
        self.assertIsNone(self.task_id_by_title('Задача на удаление'))

    def test_foreign_task_returns_404(self):
        """Задачи другого пользователя не открываются (IDOR-защита)."""
        self.create_task()
        task_id = self.task_id_by_title('Тестовая задача')
        other = make_client()
        register_and_login(other, 'tasks-unittest-2@example.com')
        self.assertEqual(other.get(f'/tasks/{task_id}/edit').status_code, 404)
        self.assertEqual(other.post(f'/tasks/{task_id}/delete').status_code, 404)

    def test_overdue_badge(self):
        """Просроченная невыполненная задача помечается в списке."""
        self.create_task(title='Просрочка', deadline='2026-01-01')
        self.assertIn('просрочена', self.c.get('/').get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
