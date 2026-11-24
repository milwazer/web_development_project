"""Тесты профиля и смены пароля (ФР-13, ФР-14)."""
import unittest

import db

from tests import make_client, register_and_login, drop_user, post, TEST_PASSWORD

TEST_EMAIL = 'profile-unittest@example.com'


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.c = make_client()
        drop_user(TEST_EMAIL)
        register_and_login(self.c, TEST_EMAIL)
        # две задачи: одна выполнена, одна просрочена
        self.c.post('/tasks/new', data={'title': 'Выполненная', 'priority': 'низкий',
                                        'status': 'выполнена'})
        self.c.post('/tasks/new', data={'title': 'Просроченная', 'priority': 'низкий',
                                        'status': 'новая', 'deadline': '2026-01-01'})

    def tearDown(self):
        drop_user(TEST_EMAIL)

    def test_profile_shows_email_and_stats(self):
        """Профиль содержит email и правильную статистику."""
        r = self.c.get('/profile')
        html = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn(TEST_EMAIL, html)
        # всего 2, выполнена 1, просрочена 1
        self.assertIn('2', html)
        self.assertIn('Просрочено', html)

    def test_password_change_success(self):
        """Смена пароля: старый не подходит, новый работает."""
        r = post(self.c, '/profile/password', data={
            'old_password': TEST_PASSWORD, 'new_password': 'newpass123',
            'new_password2': 'newpass123'}, follow_redirects=True)
        self.assertIn('Пароль изменён', r.get_data(as_text=True))
        # вход со старым паролем больше не проходит
        fresh = make_client()
        r = post(fresh, '/login', data={'email': TEST_EMAIL,
                                        'password': TEST_PASSWORD},
                 follow_redirects=True)
        self.assertIn('Неверный email или пароль', r.get_data(as_text=True))
        # вход с новым паролем работает
        r = post(fresh, '/login', data={'email': TEST_EMAIL,
                                        'password': 'newpass123'})
        self.assertEqual(r.status_code, 302)

    def test_wrong_old_password_rejected(self):
        r = post(self.c, '/profile/password', data={
            'old_password': 'wrong-old', 'new_password': 'newpass123',
            'new_password2': 'newpass123'}, follow_redirects=True)
        self.assertIn('Текущий пароль указан неверно', r.get_data(as_text=True))

    def test_short_new_password_rejected(self):
        r = post(self.c, '/profile/password', data={
            'old_password': TEST_PASSWORD, 'new_password': '123',
            'new_password2': '123'}, follow_redirects=True)
        self.assertIn('не короче 6 символов', r.get_data(as_text=True))

    def test_mismatched_new_passwords_rejected(self):
        r = post(self.c, '/profile/password', data={
            'old_password': TEST_PASSWORD, 'new_password': 'newpass123',
            'new_password2': 'other999'}, follow_redirects=True)
        self.assertIn('не совпадают', r.get_data(as_text=True))

    def test_password_still_hashed_in_db(self):
        """В базе после смены лежит хеш, а не открытый пароль."""
        post(self.c, '/profile/password', data={
            'old_password': TEST_PASSWORD, 'new_password': 'newpass123',
            'new_password2': 'newpass123'})
        row = db.query('SELECT password_hash FROM users WHERE email = %s',
                       (TEST_EMAIL,), fetch='one')
        self.assertNotIn('newpass123', row['password_hash'])
        self.assertTrue(row['password_hash'].startswith('scrypt:'))


if __name__ == '__main__':
    unittest.main()
