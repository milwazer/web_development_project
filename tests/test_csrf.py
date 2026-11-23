"""Тесты CSRF-защиты форм."""
import re
import unittest

from tests import make_client, register_and_login, drop_user

TEST_EMAIL = 'csrf-unittest@example.com'


class CsrfTests(unittest.TestCase):
    def setUp(self):
        self.c = make_client()
        drop_user(TEST_EMAIL)
        register_and_login(self.c, TEST_EMAIL)

    def tearDown(self):
        drop_user(TEST_EMAIL)

    def form_token(self, url):
        """Вытаскивает CSRF-токен из HTML формы."""
        html = self.c.get(url).get_data(as_text=True)
        match = re.search(r'name="csrf_token" value="([0-9a-f]+)"', html)
        return match.group(1) if match else None

    def test_post_without_token_rejected(self):
        """POST без токена отклоняется с 400."""
        r = self.c.post('/tasks/new', data={'title': 'Без токена'})
        self.assertEqual(r.status_code, 400)

    def test_post_with_wrong_token_rejected(self):
        """POST с чужим токеном отклоняется с 400."""
        r = self.c.post('/tasks/new', data={'title': 'x', 'csrf_token': 'bad'})
        self.assertEqual(r.status_code, 400)

    def test_post_with_valid_token_passes(self):
        """POST с токеном из формы проходит штатно."""
        token = self.form_token('/tasks/new')
        self.assertIsNotNone(token)
        r = self.c.post('/tasks/new', data={'title': 'С токеном',
                                            'priority': 'средний',
                                            'status': 'новая',
                                            'csrf_token': token})
        self.assertEqual(r.status_code, 302)


if __name__ == '__main__':
    unittest.main()
