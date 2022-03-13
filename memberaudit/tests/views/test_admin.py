from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from ...models import SkillSet
from ...views.admin import admin_create_skillset_from_fitting
from ..testdata.factories import (
    create_fitting_text,
    create_skill_set,
    create_skill_set_group,
)
from ..testdata.load_entities import load_entities
from ..testdata.load_eveuniverse import load_eveuniverse

MODULE_PATH = "memberaudit.views.admin"


@patch(MODULE_PATH + ".messages", spec=True)
@patch(MODULE_PATH + ".tasks", spec=True)
class TestCreateSkillSetFromFitting(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        load_eveuniverse()
        load_entities()
        cls.superuser = User.objects.create_superuser("Superman")
        cls.fitting_text = create_fitting_text("fitting_tristan.txt")

    def test_should_open_page(self, mock_tasks, mock_messages):
        # given
        request = self.factory.get(
            reverse("memberaudit:admin_create_skillset_from_fitting")
        )
        request.user = self.superuser
        # when
        response = admin_create_skillset_from_fitting(request)
        # then
        self.assertEqual(response.status_code, 200)

    def test_should_create_new_skillset(self, mock_tasks, mock_messages):
        # given
        request = self.factory.post(
            reverse("memberaudit:admin_create_skillset_from_fitting"),
            data={"fitting_text": self.fitting_text},
        )
        request.user = self.superuser
        # when
        response = admin_create_skillset_from_fitting(request)
        # then
        self.assertEqual(response.status_code, 302)
        self.assertTrue(mock_tasks.update_characters_skill_checks.delay.called)
        self.assertTrue(mock_messages.info.called)
        self.assertEqual(SkillSet.objects.count(), 1)

    def test_should_not_overwrite_existing_skillset(self, mock_tasks, mock_messages):
        # given
        skill_set = create_skill_set(name="Tristan - Standard Kite (cap stable)")
        request = self.factory.post(
            reverse("memberaudit:admin_create_skillset_from_fitting"),
            data={"fitting_text": self.fitting_text},
        )
        request.user = self.superuser
        # when
        response = admin_create_skillset_from_fitting(request)
        # then
        self.assertEqual(response.status_code, 302)
        self.assertTrue(mock_messages.warning.called)
        self.assertFalse(mock_tasks.update_characters_skill_checks.delay.called)
        skill_set.refresh_from_db()
        self.assertEqual(skill_set.skills.count(), 0)

    def test_should_overwrite_existing_skillset(self, mock_tasks, mock_messages):
        # given
        skill_set = create_skill_set(name="Tristan - Standard Kite (cap stable)")
        request = self.factory.post(
            reverse("memberaudit:admin_create_skillset_from_fitting"),
            data={"fitting_text": self.fitting_text, "can_overwrite": True},
        )
        request.user = self.superuser
        # when
        response = admin_create_skillset_from_fitting(request)
        # then
        self.assertEqual(response.status_code, 302)
        self.assertTrue(mock_tasks.update_characters_skill_checks.delay.called)
        self.assertTrue(mock_messages.warning.info)
        skill_set.refresh_from_db()
        self.assertGreater(skill_set.skills.count(), 0)

    def test_should_create_new_skillset_and_assign_group(
        self, mock_tasks, mock_messages
    ):
        # given
        skill_set_group = create_skill_set_group()
        request = self.factory.post(
            reverse("memberaudit:admin_create_skillset_from_fitting"),
            data={
                "fitting_text": self.fitting_text,
                "skill_set_group": skill_set_group.id,
            },
        )
        request.user = self.superuser
        # when
        response = admin_create_skillset_from_fitting(request)
        # then
        self.assertEqual(response.status_code, 302)
        self.assertTrue(mock_messages.info.called)
        self.assertTrue(mock_tasks.update_characters_skill_checks.delay.called)
        skill_set = SkillSet.objects.first()
        self.assertIn(skill_set, skill_set_group.skill_sets.all())

    def test_should_create_new_skillset_with_custom_name(
        self, mock_tasks, mock_messages
    ):
        # given
        skill_set = create_skill_set(name="Tristan - Standard Kite (cap stable)")
        request = self.factory.post(
            reverse("memberaudit:admin_create_skillset_from_fitting"),
            data={"fitting_text": self.fitting_text, "skill_set_name": "My-Name"},
        )
        request.user = self.superuser
        # when
        response = admin_create_skillset_from_fitting(request)
        # then
        self.assertEqual(response.status_code, 302)
        self.assertTrue(mock_tasks.update_characters_skill_checks.delay.called)
        self.assertTrue(mock_messages.info.called)
        skill_set = SkillSet.objects.last()
        self.assertEqual(skill_set.name, "My-Name")
