"""Тесты панели администратора (роли, блокировка, каскадное удаление)."""
import unittest

import db

from tests import make_client, register_and_login, drop_user, TEST_PASSWORD

TEST_EMAIL = 'admin-unittest@example.com'


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.admin = make_client()
        self.admin.post('/login', data={'email': 'admin@example.com',
                                        'password': 'admin123'})

    def tearDown(self):
        drop_user(TEST_EMAIL)

    def test_admin_panel_visible_for_admin(self):
        r = self.admin.get('/admin')
        self.assertEqual(r.status_code, 200)
        self.assertIn('admin@example.com', r.get_data(as_text=True))

    def test_panel_hidden_for_regular_user(self):
        other = make_client()
        register_and_login(other, TEST_EMAIL)
        self.assertEqual(other.get('/admin').status_code, 404)

    def test_panel_hidden_for_guest(self):
        self.assertEqual(make_client().get('/admin').status_code, 404)

    def test_email_search(self):
        r = self.admin.get('/admin?q=user')
        html = r.get_data(as_text=True)
        self.assertIn('user@example.com', html)
        self.assertNotIn('spam@example.com', html)

    def test_block_unblock_cycle(self):
        """Заблокированный не входит; после разблокировки — входит."""
        register_and_login(make_client(), TEST_EMAIL)
        self.admin.post('/admin/2/block')  # user@example.com, id = 2
        c = make_client()
        r = c.post('/login', data={'email': 'user@example.com',
                                   'password': 'user123'}, follow_redirects=True)
        self.assertIn('заблокирован', r.get_data(as_text=True))
        self.admin.post('/admin/2/unblock')
        r = c.post('/login', data={'email': 'user@example.com',
                                   'password': 'user123'})
        self.assertEqual(r.status_code, 302)

    def test_cannot_block_yourself(self):
        r = self.admin.post('/admin/1/block', follow_redirects=True)
        self.assertIn('Нельзя заблокировать самого себя',
                      r.get_data(as_text=True))
        self.assertFalse(db.query('SELECT is_blocked FROM users WHERE id = 1',
                                  fetch='one')['is_blocked'])

    def test_delete_cascades_tasks_and_categories(self):
        """Удаление пользователя убирает его задачи и категории (ФР-17)."""
        register_and_login(make_client(), TEST_EMAIL)
        c = make_client()
        c.post('/login', data={'email': TEST_EMAIL, 'password': TEST_PASSWORD})
        c.post('/categories', data={'name': 'Категория на удаление'})
        c.post('/tasks/new', data={'title': 'Задача на удаление',
                                   'priority': 'низкий', 'status': 'новая'})
        user_id = db.query('SELECT id FROM users WHERE email = %s',
                           (TEST_EMAIL,), fetch='one')['id']
        r = self.admin.post(f'/admin/{user_id}/delete', follow_redirects=True)
        self.assertIn('Пользователь удалён', r.get_data(as_text=True))
        self.assertIsNone(db.query('SELECT id FROM users WHERE email = %s',
                                   (TEST_EMAIL,), fetch='one'))
        self.assertIsNone(db.query('SELECT id FROM tasks WHERE title = %s',
                                   ('Задача на удаление',), fetch='one'))
        self.assertIsNone(db.query('SELECT id FROM categories WHERE name = %s',
                                   ('Категория на удаление',), fetch='one'))


if __name__ == '__main__':
    unittest.main()
