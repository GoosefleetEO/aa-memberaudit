import datetime as dt

from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import now
from eveuniverse.models import EveEntity, EveType

from app_utils.testing import (
    generate_invalid_pk,
    json_response_to_dict,
    json_response_to_python,
    multi_assert_in,
    response_text,
)

from ..models import (
    CharacterAsset,
    CharacterAttributes,
    CharacterContact,
    CharacterCorporationHistory,
    CharacterImplant,
    CharacterJumpClone,
    CharacterJumpCloneImplant,
    CharacterLoyaltyEntry,
    CharacterSkill,
    CharacterSkillqueueEntry,
    CharacterWalletJournalEntry,
    CharacterWalletTransaction,
    Location,
    SkillSet,
    SkillSetGroup,
    SkillSetSkill,
)
from ..views.character_viewer import (
    character_asset_container,
    character_asset_container_data,
    character_assets_data,
    character_attribute_data,
    character_contacts_data,
    character_corporation_history,
    character_implants_data,
    character_jump_clones_data,
    character_loyalty_data,
    character_skill_set_details,
    character_skill_sets_data,
    character_skillqueue_data,
    character_skills_data,
    character_viewer,
    character_wallet_journal_data,
    character_wallet_transactions_data,
)
from .utils import LoadTestDataMixin

MODULE_PATH = "memberaudit.views.character_viewer"


class TestCharacterViewer(LoadTestDataMixin, TestCase):
    def test_can_open_character_main_view(self):
        request = self.factory.get(
            reverse("memberaudit:character_viewer", args=[self.character.pk])
        )
        request.user = self.user
        response = character_viewer(request, self.character.pk)
        self.assertEqual(response.status_code, 200)

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

    def test_character_attribute_data(self):
        CharacterAttributes.objects.create(
            character=self.character,
            last_remap_date="2020-10-24T09:00:00Z",
            bonus_remaps=3,
            charisma=100,
            intelligence=101,
            memory=102,
            perception=103,
            willpower=104,
        )

        request = self.factory.get(
            reverse(
                "memberaudit:character_attribute_data",
                args=[self.character.pk],
            )
        )

        request.user = self.user
        response = character_attribute_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)


class TestCharacterAssets(LoadTestDataMixin, TestCase):
    def test_character_assets_data_1(self):
        container = CharacterAsset.objects.create(
            character=self.character,
            item_id=1,
            location=self.jita_44,
            eve_type=EveType.objects.get(id=20185),
            is_singleton=True,
            name="Trucker",
            quantity=1,
        )
        CharacterAsset.objects.create(
            character=self.character,
            item_id=2,
            parent=container,
            eve_type=EveType.objects.get(id=603),
            is_singleton=False,
            quantity=1,
        )

        request = self.factory.get(
            reverse("memberaudit:character_assets_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_assets_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(row["item_id"], 1)
        self.assertEqual(
            row["location"], "Jita IV - Moon 4 - Caldari Navy Assembly Plant (1)"
        )
        self.assertEqual(row["name"]["sort"], "Trucker")
        self.assertEqual(row["quantity"], "")
        self.assertEqual(row["group"], "Charon")
        self.assertEqual(row["volume"], 16250000.0)
        self.assertEqual(row["solar_system"], "Jita")
        self.assertEqual(row["region"], "The Forge")
        self.assertTrue(row["actions"])

    def test_character_assets_data_2(self):
        CharacterAsset.objects.create(
            character=self.character,
            item_id=1,
            location=self.jita_44,
            eve_type=EveType.objects.get(id=20185),
            is_singleton=False,
            name="",
            quantity=1,
        )
        request = self.factory.get(
            reverse("memberaudit:character_assets_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_assets_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(row["item_id"], 1)
        self.assertEqual(
            row["location"], "Jita IV - Moon 4 - Caldari Navy Assembly Plant (1)"
        )
        self.assertEqual(row["name"]["sort"], "Charon")
        self.assertEqual(row["quantity"], 1)
        self.assertEqual(row["group"], "Freighter")
        self.assertEqual(row["volume"], 16250000.0)
        self.assertFalse(row["actions"])

    def test_character_asset_children_normal(self):
        parent_asset = CharacterAsset.objects.create(
            character=self.character,
            item_id=1,
            location=self.jita_44,
            eve_type=EveType.objects.get(id=20185),
            is_singleton=True,
            name="Trucker",
            quantity=1,
        )
        CharacterAsset.objects.create(
            character=self.character,
            item_id=2,
            parent=parent_asset,
            eve_type=EveType.objects.get(id=603),
            is_singleton=True,
            name="My Precious",
            quantity=1,
        )
        request = self.factory.get(
            reverse(
                "memberaudit:character_asset_container",
                args=[self.character.pk, parent_asset.pk],
            )
        )
        request.user = self.user
        response = character_asset_container(
            request, self.character.pk, parent_asset.pk
        )
        self.assertEqual(response.status_code, 200)

    def test_character_asset_children_error(self):
        parent_asset_pk = generate_invalid_pk(CharacterAsset)
        request = self.factory.get(
            reverse(
                "memberaudit:character_asset_container",
                args=[self.character.pk, parent_asset_pk],
            )
        )
        request.user = self.user
        response = character_asset_container(
            request, self.character.pk, parent_asset_pk
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("not found for character", response_text(response))

    def test_character_asset_children_data(self):
        parent_asset = CharacterAsset.objects.create(
            character=self.character,
            item_id=1,
            location=self.jita_44,
            eve_type=EveType.objects.get(id=20185),
            is_singleton=True,
            name="Trucker",
            quantity=1,
        )
        CharacterAsset.objects.create(
            character=self.character,
            item_id=2,
            parent=parent_asset,
            eve_type=EveType.objects.get(id=603),
            is_singleton=True,
            name="My Precious",
            quantity=1,
        )
        CharacterAsset.objects.create(
            character=self.character,
            item_id=3,
            parent=parent_asset,
            eve_type=EveType.objects.get(id=19540),
            is_singleton=False,
            quantity=3,
        )
        request = self.factory.get(
            reverse(
                "memberaudit:character_asset_container_data",
                args=[self.character.pk, parent_asset.pk],
            )
        )
        request.user = self.user
        response = character_asset_container_data(
            request, self.character.pk, parent_asset.pk
        )
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 2)

        row = data[0]
        self.assertEqual(row["item_id"], 2)
        self.assertEqual(row["name"]["sort"], "My Precious")
        self.assertEqual(row["quantity"], "")
        self.assertEqual(row["group"], "Merlin")
        self.assertEqual(row["volume"], 16500.0)

        row = data[1]
        self.assertEqual(row["item_id"], 3)
        self.assertEqual(row["name"]["sort"], "High-grade Snake Alpha")
        self.assertEqual(row["quantity"], 3)
        self.assertEqual(row["group"], "Cyberimplant")
        self.assertEqual(row["volume"], 1.0)


class TestCharacterDataViewsOther(LoadTestDataMixin, TestCase):
    def test_character_contacts_data(self):
        CharacterContact.objects.create(
            character=self.character,
            eve_entity=EveEntity.objects.get(id=1101),
            standing=-10,
            is_blocked=True,
        )
        CharacterContact.objects.create(
            character=self.character,
            eve_entity=EveEntity.objects.get(id=2001),
            standing=10,
        )

        request = self.factory.get(
            reverse("memberaudit:character_contacts_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_contacts_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_dict(response)

        self.assertEqual(len(data), 2)

        row = data[1101]
        self.assertEqual(row["name"]["sort"], "Lex Luther")
        self.assertEqual(row["standing"], -10)
        self.assertEqual(row["type"], "Character")
        self.assertEqual(row["is_watched"], False)
        self.assertEqual(row["is_blocked"], True)
        self.assertEqual(row["level"], "Terrible Standing")

        row = data[2001]
        self.assertEqual(row["name"]["sort"], "Wayne Technologies")
        self.assertEqual(row["standing"], 10)
        self.assertEqual(row["type"], "Corporation")
        self.assertEqual(row["is_watched"], False)
        self.assertEqual(row["is_blocked"], False)
        self.assertEqual(row["level"], "Excellent Standing")

    def test_character_jump_clones_data(self):
        clone_1 = jump_clone = CharacterJumpClone.objects.create(
            character=self.character, location=self.jita_44, jump_clone_id=1
        )
        CharacterJumpCloneImplant.objects.create(
            jump_clone=jump_clone, eve_type=EveType.objects.get(id=19540)
        )
        CharacterJumpCloneImplant.objects.create(
            jump_clone=jump_clone, eve_type=EveType.objects.get(id=19551)
        )

        location_2 = Location.objects.create(id=123457890)
        clone_2 = jump_clone = CharacterJumpClone.objects.create(
            character=self.character, location=location_2, jump_clone_id=2
        )
        request = self.factory.get(
            reverse("memberaudit:character_jump_clones_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_jump_clones_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_dict(response)
        self.assertEqual(len(data), 2)

        row = data[clone_1.pk]
        self.assertEqual(row["region"], "The Forge")
        self.assertIn("Jita", row["solar_system"])
        self.assertEqual(
            row["location"], "Jita IV - Moon 4 - Caldari Navy Assembly Plant"
        )
        self.assertTrue(
            multi_assert_in(
                ["High-grade Snake Alpha", "High-grade Snake Beta"], row["implants"]
            )
        )

        row = data[clone_2.pk]
        self.assertEqual(row["region"], "-")
        self.assertEqual(row["solar_system"], "-")
        self.assertEqual(row["location"], "Unknown location #123457890")
        self.assertEqual(row["implants"], "(none)")

    def test_character_loyalty_data(self):
        CharacterLoyaltyEntry.objects.create(
            character=self.character,
            corporation=EveEntity.objects.get(id=2101),
            loyalty_points=99,
        )
        request = self.factory.get(
            reverse("memberaudit:character_loyalty_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_loyalty_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(row["corporation"]["sort"], "Lexcorp")
        self.assertEqual(row["loyalty_points"], 99)

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

    def test_character_corporation_history(self):
        """
        when corp history contains two corporations
        and one corp is deleted,
        then both corporation names can be found in the view data
        """
        date_1 = now() - dt.timedelta(days=60)
        CharacterCorporationHistory.objects.create(
            character=self.character,
            record_id=1,
            corporation=EveEntity.objects.get(id=2101),
            start_date=date_1,
        )
        date_2 = now() - dt.timedelta(days=20)
        CharacterCorporationHistory.objects.create(
            character=self.character,
            record_id=2,
            corporation=EveEntity.objects.get(id=2001),
            start_date=date_2,
            is_deleted=True,
        )
        request = self.factory.get(
            reverse(
                "memberaudit:character_corporation_history", args=[self.character.pk]
            )
        )
        request.user = self.user
        response = character_corporation_history(request, self.character.pk)

        self.assertEqual(response.status_code, 200)
        text = response.content.decode("utf-8")
        self.assertIn(EveEntity.objects.get(id=2101).name, text)
        self.assertIn(EveEntity.objects.get(id=2001).name, text)
        self.assertIn("(Closed)", text)

    def test_character_character_implants_data(self):
        implant_1 = CharacterImplant.objects.create(
            character=self.character, eve_type=EveType.objects.get(id=19553)
        )
        implant_2 = CharacterImplant.objects.create(
            character=self.character, eve_type=EveType.objects.get(id=19540)
        )
        implant_3 = CharacterImplant.objects.create(
            character=self.character, eve_type=EveType.objects.get(id=19551)
        )
        request = self.factory.get(
            reverse("memberaudit:character_implants_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_implants_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)

        data = json_response_to_dict(response)
        self.assertSetEqual(
            set(data.keys()), {implant_1.pk, implant_2.pk, implant_3.pk}
        )
        self.assertIn(
            "High-grade Snake Gamma",
            data[implant_1.pk]["implant"]["display"],
        )
        self.assertEqual(data[implant_1.pk]["implant"]["sort"], 3)
