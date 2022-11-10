from django.test import TestCase
from django.urls import reverse

from app_utils.testing import create_user_from_evecharacter

from ...views.data_export import data_export
from ..utils import LoadTestDataMixin

MODULE_PATH = "memberaudit.views.data_export"


class TestDataExport(LoadTestDataMixin, TestCase):
    def test_should_open_exports_page_with_permission(self):
        # given
        user, _ = create_user_from_evecharacter(
            1122, permissions=["memberaudit.basic_access", "memberaudit.exports_access"]
        )
        request = self.factory.get(reverse("memberaudit:data_export"))
        request.user = user
        # when
        response = data_export(request)
        # then
        self.assertEqual(response.status_code, 200)

    def test_should_not_open_exports_page_without_permission(self):
        # given
        user, _ = create_user_from_evecharacter(
            1122, permissions=["memberaudit.basic_access"]
        )
        request = self.factory.get(reverse("memberaudit:data_export"))
        request.user = user
        # when
        response = data_export(request)
        # then
        self.assertEqual(response.status_code, 302)
