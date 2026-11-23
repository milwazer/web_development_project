"""Тесты пагинации списка задач (10 задач на страницу)."""
import unittest

from tests import post, make_client, register_and_login, drop_user

TEST_EMAIL = 'pagination-unittest@example.com'


class PaginationTests(unittest.TestCase):
    def setUp(self):
        self.c = make_client()
        drop_user(TEST_EMAIL)
        register_and_login(self.c, TEST_EMAIL)
        # 12 задач -> две страницы
        for i in range(1, 13):
            post(self.c, '/tasks/new', data={'title': f'Задача №{i}',
                                            'priority': 'средний',
                                            'status': 'новая'})

    def tearDown(self):
        drop_user(TEST_EMAIL)

    def test_first_page_shows_ten(self):
        r = self.c.get('/')
        self.assertIn('Показано 10 из 12 задач', r.get_data(as_text=True))

    def test_second_page_shows_rest(self):
        r = self.c.get('/?page=2')
        self.assertIn('Показано 2 из 12 задач', r.get_data(as_text=True))

    def test_page_beyond_range_clamped(self):
        r = self.c.get('/?page=99')
        self.assertIn('Показано 2 из 12 задач', r.get_data(as_text=True))

    def test_garbage_page_falls_back_to_first(self):
        r = self.c.get('/?page=abc')
        self.assertIn('Показано 10 из 12 задач', r.get_data(as_text=True))

    def test_filters_kept_in_page_links(self):
        """Ссылки пагинации сохраняют активные фильтры."""
        r = self.c.get('/?q=%D0%97%D0%B0%D0%B4%D0%B0%D1%87%D0%B0')  # «Задача»
        html = r.get_data(as_text=True)
        self.assertIn('page=2', html)

    def test_no_pagination_for_short_list(self):
        """У пользователя с <= 10 задачами навигации нет."""
        drop_user(TEST_EMAIL)
        register_and_login(self.c, TEST_EMAIL)
        html = self.c.get('/').get_data(as_text=True)
        self.assertNotIn('page-link', html)


if __name__ == '__main__':
    unittest.main()
