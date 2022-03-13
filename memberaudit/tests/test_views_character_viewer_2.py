import datetime as dt

from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import now
from eveuniverse.models import EveEntity, EveType

from app_utils.testing import json_response_to_python, response_text

from ..models import (
    CharacterSkill,
    CharacterSkillqueueEntry,
    CharacterWalletJournalEntry,
    CharacterWalletTransaction,
    Location,
    SkillSet,
    SkillSetGroup,
    SkillSetSkill,
)
from ..views.character_viewer_2 import (
    character_skill_set_details,
    character_skill_sets_data,
    character_skillqueue_data,
    character_skills_data,
    character_wallet_journal_data,
    character_wallet_transactions_data,
)
from .utils import LoadTestDataMixin

MODULE_PATH = "memberaudit.views.character_viewer_2"


class TestSkillSets(LoadTestDataMixin, TestCase):
    def test_skill_sets_data(self):
        CharacterSkill.objects.create(
            character=self.character,
            eve_type=self.skill_type_1,
            active_skill_level=4,
            skillpoints_in_skill=10,
            trained_skill_level=4,
        )
        CharacterSkill.objects.create(
            character=self.character,
            eve_type=self.skill_type_2,
            active_skill_level=2,
            skillpoints_in_skill=10,
            trained_skill_level=5,
        )

        doctrine_1 = SkillSetGroup.objects.create(name="Alpha")
        doctrine_2 = SkillSetGroup.objects.create(name="Bravo", is_doctrine=True)

        # can fly ship 1
        ship_1 = SkillSet.objects.create(name="Ship 1")
        SkillSetSkill.objects.create(
            skill_set=ship_1,
            eve_type=self.skill_type_1,
            required_level=3,
            recommended_level=5,
        )
        doctrine_1.skill_sets.add(ship_1)
        doctrine_2.skill_sets.add(ship_1)

        # can not fly ship 2
        ship_2 = SkillSet.objects.create(name="Ship 2")
        SkillSetSkill.objects.create(
            skill_set=ship_2, eve_type=self.skill_type_1, required_level=3
        )
        SkillSetSkill.objects.create(
            skill_set=ship_2, eve_type=self.skill_type_2, required_level=3
        )
        doctrine_1.skill_sets.add(ship_2)

        # can fly ship 3 (No SkillSetGroup)
        ship_3 = SkillSet.objects.create(name="Ship 3")
        SkillSetSkill.objects.create(
            skill_set=ship_3, eve_type=self.skill_type_1, required_level=1
        )

        self.character.update_skill_sets()

        request = self.factory.get(
            reverse("memberaudit:character_skill_sets_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_skill_sets_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 4)

        row = data[0]
        self.assertEqual(row["group"], "[Ungrouped]")
        self.assertEqual(row["skill_set_name"], "Ship 3")
        self.assertTrue(row["has_required"])
        self.assertEqual(row["failed_required_skills"], "-")

        row = data[1]
        self.assertEqual(row["group"], "Alpha")
        self.assertEqual(row["skill_set_name"], "Ship 1")
        self.assertTrue(row["has_required"])
        self.assertEqual(row["failed_required_skills"], "-")
        self.assertIn("Amarr Carrier&nbsp;V", row["failed_recommended_skills"])

        row = data[2]
        self.assertEqual(row["group"], "Alpha")
        self.assertEqual(row["skill_set_name"], "Ship 2")
        self.assertFalse(row["has_required"])
        self.assertIn("Caldari Carrier&nbsp;III", row["failed_required_skills"])

        row = data[3]
        self.assertEqual(row["group"], "Doctrine: Bravo")
        self.assertEqual(row["skill_set_name"], "Ship 1")
        self.assertTrue(row["has_required"])
        self.assertEqual(row["failed_required_skills"], "-")

    def test_skill_set_details(self):
        CharacterSkill.objects.create(
            character=self.character,
            eve_type=self.skill_type_1,
            active_skill_level=4,
            skillpoints_in_skill=10,
            trained_skill_level=4,
        )
        CharacterSkill.objects.create(
            character=self.character,
            eve_type=self.skill_type_2,
            active_skill_level=2,
            skillpoints_in_skill=10,
            trained_skill_level=2,
        )
        CharacterSkill.objects.create(
            character=self.character,
            eve_type=self.skill_type_3,
            active_skill_level=4,
            skillpoints_in_skill=10,
            trained_skill_level=4,
        )
        CharacterSkill.objects.create(
            character=self.character,
            eve_type=self.skill_type_4,
            active_skill_level=3,
            skillpoints_in_skill=10,
            trained_skill_level=3,
        )

        skill_set_1 = SkillSet.objects.create(name="skill set")
        SkillSetSkill.objects.create(
            skill_set=skill_set_1,
            eve_type=self.skill_type_1,
            required_level=3,
            recommended_level=5,
        )
        SkillSetSkill.objects.create(
            skill_set=skill_set_1,
            eve_type=self.skill_type_2,
            required_level=None,
            recommended_level=3,
        )
        SkillSetSkill.objects.create(
            skill_set=skill_set_1,
            eve_type=self.skill_type_3,
            required_level=3,
            recommended_level=None,
        )
        SkillSetSkill.objects.create(
            skill_set=skill_set_1,
            eve_type=self.skill_type_4,
            required_level=None,
            recommended_level=None,
        )

        request = self.factory.get(
            reverse(
                "memberaudit:character_skill_set_details",
                args=[self.character.pk, skill_set_1.pk],
            )
        )

        request.user = self.user
        response = character_skill_set_details(
            request, self.character.pk, skill_set_1.pk
        )
        self.assertEqual(response.status_code, 200)

        text = response_text(response)

        self.assertIn(skill_set_1.name, text)
        self.assertIn(self.skill_type_1.name, text)
        self.assertIn(self.skill_type_2.name, text)
        self.assertIn(self.skill_type_3.name, text)
        self.assertIn(self.skill_type_4.name, text)


class TestSkillAndSkillqueue(LoadTestDataMixin, TestCase):
    def test_character_skills_data(self):
        CharacterSkill.objects.create(
            character=self.character,
            eve_type=self.skill_type_1,
            active_skill_level=1,
            skillpoints_in_skill=1000,
            trained_skill_level=1,
        )
        request = self.factory.get(
            reverse("memberaudit:character_skills_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_skills_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(row["group"], "Spaceship Command")
        self.assertEqual(row["skill"], "Amarr Carrier")
        self.assertEqual(row["level"], 1)

    def test_character_skillqueue_data_1(self):
        """Char has skills in training"""
        finish_date_1 = now() + dt.timedelta(days=3)
        CharacterSkillqueueEntry.objects.create(
            character=self.character,
            eve_type=self.skill_type_1,
            finish_date=finish_date_1,
            finished_level=5,
            queue_position=0,
            start_date=now() - dt.timedelta(days=1),
        )
        finish_date_2 = now() + dt.timedelta(days=10)
        CharacterSkillqueueEntry.objects.create(
            character=self.character,
            eve_type=self.skill_type_2,
            finish_date=finish_date_2,
            finished_level=5,
            queue_position=1,
            start_date=now() - dt.timedelta(days=1),
        )
        request = self.factory.get(
            reverse("memberaudit:character_skillqueue_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_skillqueue_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 2)

        row = data[0]
        self.assertEqual(row["skill"], "Amarr Carrier&nbsp;V [ACTIVE]")
        self.assertEqual(row["finished"]["sort"], finish_date_1.isoformat())
        self.assertTrue(row["is_active"])

        row = data[1]
        self.assertEqual(row["skill"], "Caldari Carrier&nbsp;V")
        self.assertEqual(row["finished"]["sort"], finish_date_2.isoformat())
        self.assertFalse(row["is_active"])

    def test_character_skillqueue_data_2(self):
        """Char has no skills in training"""
        CharacterSkillqueueEntry.objects.create(
            character=self.character,
            eve_type=self.skill_type_1,
            finished_level=5,
            queue_position=0,
        )
        request = self.factory.get(
            reverse("memberaudit:character_skillqueue_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_skillqueue_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(row["skill"], "Amarr Carrier&nbsp;V")
        self.assertIsNone(row["finished"]["sort"])
        self.assertFalse(row["is_active"])


class TestWallet(LoadTestDataMixin, TestCase):
    def test_character_wallet_journal_data(self):
        CharacterWalletJournalEntry.objects.create(
            character=self.character,
            entry_id=1,
            amount=1000000,
            balance=10000000,
            context_id_type=CharacterWalletJournalEntry.CONTEXT_ID_TYPE_UNDEFINED,
            date=now(),
            description="dummy",
            first_party=EveEntity.objects.get(id=1001),
            second_party=EveEntity.objects.get(id=1002),
        )
        request = self.factory.get(
            reverse(
                "memberaudit:character_wallet_journal_data", args=[self.character.pk]
            )
        )
        request.user = self.user
        response = character_wallet_journal_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(row["amount"], 1000000.00)
        self.assertEqual(row["balance"], 10000000.00)

    def test_character_wallet_transaction_data(self):
        my_date = now()
        CharacterWalletTransaction.objects.create(
            character=self.character,
            transaction_id=42,
            client=EveEntity.objects.get(id=1002),
            date=my_date,
            is_buy=True,
            is_personal=True,
            location=Location.objects.get(id=60003760),
            quantity=3,
            eve_type=EveType.objects.get(id=603),
            unit_price=450000.99,
        )
        request = self.factory.get(
            reverse(
                "memberaudit:character_wallet_transactions_data",
                args=[self.character.pk],
            )
        )
        request.user = self.user
        response = character_wallet_transactions_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(row["date"], my_date.isoformat())
        self.assertEqual(row["quantity"], 3)
        self.assertEqual(row["type"], "Merlin")
        self.assertEqual(row["unit_price"], 450_000.99)
        self.assertEqual(row["total"], -1_350_002.97)
        self.assertEqual(row["client"], "Clark Kent")
        self.assertEqual(
            row["location"], "Jita IV - Moon 4 - Caldari Navy Assembly Plant"
        )
