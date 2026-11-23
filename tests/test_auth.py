"""Тесты регистрации и авторизации."""
import unittest

from tests import post, make_client, register_and_login, drop_user, TEST_PASSWORD

SEED_EMAIL = 'user@example.com'
TEST_EMAIL = 'auth-unittest@example.com'


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.c = make_client()
        drop_user(TEST_EMAIL)

    def tearDown(self):
        drop_user(TEST_EMAIL)

    def test_guest_redirects_to_login(self):
        """Гость с главной страницы уходит на /login."""
        r = self.c.get('/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r.headers['Location'])

    def test_register_and_auto_login(self):
        """После регистрации пользователь сразу входит в аккаунт."""
        r = register_and_login(self.c, TEST_EMAIL)
        self.assertEqual(r.status_code, 302)
        self.assertIn(TEST_EMAIL, self.c.get('/').get_data(as_text=True))

    def test_duplicate_email_rejected(self):
        """Повторная регистрация существующего email отклоняется."""
        r = post(self.c, '/register', data={'email': SEED_EMAIL,
                                           'password': TEST_PASSWORD,
                                           'password2': TEST_PASSWORD},
                        follow_redirects=True)
        self.assertIn('уже зарегистрирован', r.get_data(as_text=True))

    def test_short_password_rejected(self):
        """Пароль короче 6 символов отклоняется."""
        r = post(self.c, '/register', data={'email': TEST_EMAIL, 'password': '123',
                                           'password2': '123'},
                        follow_redirects=True)
        self.assertIn('не короче 6 символов', r.get_data(as_text=True))

    def test_mismatched_passwords_rejected(self):
        """Несовпадающие пароли отклоняются."""
        r = post(self.c, '/register', data={'email': TEST_EMAIL, 'password': 'test123',
                                           'password2': 'test999'},
                        follow_redirects=True)
        self.assertIn('Пароли не совпадают', r.get_data(as_text=True))

    def test_wrong_password_login(self):
        """Вход с неверным паролем отклоняется (без раскрытия email)."""
        r = post(self.c, '/login', data={'email': SEED_EMAIL, 'password': 'nope123'},
                        follow_redirects=True)
        self.assertIn('Неверный email или пароль', r.get_data(as_text=True))

    def test_blocked_user_cannot_login(self):
        """Заблокированный пользователь не может войти (spam@example.com)."""
        r = post(self.c, '/login', data={'email': 'spam@example.com',
                                        'password': 'spam123'},
                        follow_redirects=True)
        self.assertIn('заблокирован', r.get_data(as_text=True))

    def test_logout_ends_session(self):
        """После выхода доступ к страницам снова закрыт."""
        register_and_login(self.c, TEST_EMAIL)
        self.c.get('/logout')
        self.assertEqual(self.c.get('/').status_code, 302)


if __name__ == '__main__':
    unittest.main()
