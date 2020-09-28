from django.test import TestCase, RequestFactory

from ..templatetags.memberaudit import navactive_2


class TestNavactive2(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_simple_return_active_when_matches(self):
        request = self.factory.get("/memberaudit/add_owner")
        result = navactive_2(request, "memberaudit:add_owner")
        self.assertEqual(result, "active")

    def test_simple_return_emtpy_when_no_match(self):
        request = self.factory.get("/memberaudit/add_owner")
        result = navactive_2(request, "memberaudit:reports")
        self.assertEqual(result, "")

    def test_complex_return_active_when_matches(self):
        request = self.factory.get("/memberaudit/character_main/2/")
        result = navactive_2(request, "memberaudit:character_main", 2)
        self.assertEqual(result, "active")
