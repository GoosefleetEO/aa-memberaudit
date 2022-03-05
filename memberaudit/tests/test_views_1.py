import datetime as dt
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytz

from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils.timezone import now
from eveuniverse.models import EveEntity, EveMarketPrice, EveSolarSystem, EveType

from allianceauth.tests.auth_utils import AuthUtils
from app_utils.testing import (
    create_user_from_evecharacter,
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
    CharacterContract,
    CharacterContractItem,
    CharacterCorporationHistory,
    CharacterImplant,
    CharacterJumpClone,
    CharacterJumpCloneImplant,
    CharacterLocation,
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
from ..views import (
    character_asset_container,
    character_asset_container_data,
    character_assets_data,
    character_attribute_data,
    character_contacts_data,
    character_contract_details,
    character_contract_items_included_data,
    character_contract_items_requested_data,
    character_contracts_data,
    character_corporation_history,
    character_finder,
    character_finder_data,
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
    data_export,
    data_export_run_update,
    download_export_file,
    index,
    launcher,
    reports,
)
from .testdata.load_entities import load_entities
from .testdata.load_eveuniverse import load_eveuniverse
from .testdata.load_locations import load_locations
from .utils import add_memberaudit_character_to_user, create_memberaudit_character

MODULE_PATH = "memberaudit.views"


class LoadTestDataMixin:
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        load_eveuniverse()
        load_entities()
        load_locations()
        cls.character = create_memberaudit_character(1001)
        cls.user = cls.character.character_ownership.user
        cls.jita = EveSolarSystem.objects.get(id=30000142)
        cls.jita_trade_hub = EveType.objects.get(id=52678)
        cls.corporation_2001 = EveEntity.objects.get(id=2001)
        cls.jita_44 = Location.objects.get(id=60003760)
        cls.structure_1 = Location.objects.get(id=1000000000001)
        cls.skill_type_1 = EveType.objects.get(id=24311)
        cls.skill_type_2 = EveType.objects.get(id=24312)
        cls.skill_type_3 = EveType.objects.get(id=24313)
        cls.skill_type_4 = EveType.objects.get(id=24314)
        cls.item_type_1 = EveType.objects.get(id=19540)
        cls.item_type_2 = EveType.objects.get(id=19551)


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


class TestCharacterContracts(LoadTestDataMixin, TestCase):
    @patch(MODULE_PATH + ".now")
    def test_character_contracts_data_1(self, mock_now):
        """items exchange single item"""
        date_issued = dt.datetime(2020, 10, 8, 16, 45, tzinfo=pytz.utc)
        date_now = date_issued + dt.timedelta(days=1)
        date_expired = date_now + dt.timedelta(days=2, hours=3)
        mock_now.return_value = date_now
        contract = CharacterContract.objects.create(
            character=self.character,
            contract_id=42,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_ITEM_EXCHANGE,
            assignee=EveEntity.objects.get(id=1002),
            date_issued=date_issued,
            date_expired=date_expired,
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_IN_PROGRESS,
            start_location=self.jita_44,
            end_location=self.jita_44,
            title="Dummy info",
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=1,
            is_included=True,
            is_singleton=False,
            quantity=1,
            eve_type=self.item_type_1,
        )

        # main view
        request = self.factory.get(
            reverse("memberaudit:character_contracts_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_contracts_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(row["contract_id"], 42)
        self.assertEqual(row["summary"], "High-grade Snake Alpha")
        self.assertEqual(row["type"], "Item Exchange")
        self.assertEqual(row["from"], "Bruce Wayne")
        self.assertEqual(row["to"], "Clark Kent")
        self.assertEqual(row["status"], "in progress")
        self.assertEqual(row["date_issued"], date_issued.isoformat())
        self.assertEqual(row["time_left"], "2\xa0days, 3\xa0hours")
        self.assertEqual(row["info"], "Dummy info")

        # details view
        request = self.factory.get(
            reverse(
                "memberaudit:character_contract_details",
                args=[self.character.pk, contract.pk],
            )
        )
        request.user = self.user
        response = character_contract_details(request, self.character.pk, contract.pk)
        self.assertEqual(response.status_code, 200)

    @patch(MODULE_PATH + ".now")
    def test_character_contracts_data_2(self, mock_now):
        """items exchange multiple item"""
        date_issued = dt.datetime(2020, 10, 8, 16, 45, tzinfo=pytz.utc)
        date_now = date_issued + dt.timedelta(days=1)
        date_expired = date_now + dt.timedelta(days=2, hours=3)
        mock_now.return_value = date_now
        contract = CharacterContract.objects.create(
            character=self.character,
            availability=CharacterContract.AVAILABILITY_PUBLIC,
            contract_id=42,
            contract_type=CharacterContract.TYPE_ITEM_EXCHANGE,
            assignee=EveEntity.objects.get(id=1002),
            date_issued=date_issued,
            date_expired=date_expired,
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_IN_PROGRESS,
            title="Dummy info",
            start_location=self.jita_44,
            end_location=self.jita_44,
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=1,
            is_included=True,
            is_singleton=False,
            quantity=1,
            eve_type=self.item_type_1,
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=2,
            is_included=True,
            is_singleton=False,
            quantity=1,
            eve_type=self.item_type_2,
        )
        request = self.factory.get(
            reverse("memberaudit:character_contracts_data", args=[self.character.pk])
        )

        # main view
        request.user = self.user
        response = character_contracts_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(row["contract_id"], 42)
        self.assertEqual(row["summary"], "[Multiple Items]")
        self.assertEqual(row["type"], "Item Exchange")

        # details view
        request = self.factory.get(
            reverse(
                "memberaudit:character_contract_details",
                args=[self.character.pk, contract.pk],
            )
        )
        request.user = self.user
        response = character_contract_details(request, self.character.pk, contract.pk)
        self.assertEqual(response.status_code, 200)

    @patch(MODULE_PATH + ".now")
    def test_character_contracts_data_3(self, mock_now):
        """courier contract"""
        date_issued = dt.datetime(2020, 10, 8, 16, 45, tzinfo=pytz.utc)
        date_now = date_issued + dt.timedelta(days=1)
        date_expired = date_now + dt.timedelta(days=2, hours=3)
        mock_now.return_value = date_now
        contract = CharacterContract.objects.create(
            character=self.character,
            contract_id=42,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_COURIER,
            assignee=EveEntity.objects.get(id=1002),
            date_issued=date_issued,
            date_expired=date_expired,
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_IN_PROGRESS,
            title="Dummy info",
            start_location=self.jita_44,
            end_location=self.structure_1,
            volume=10,
            days_to_complete=3,
            reward=10000000,
            collateral=500000000,
        )

        # main view
        request = self.factory.get(
            reverse("memberaudit:character_contracts_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_contracts_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(row["contract_id"], 42)
        self.assertEqual(row["summary"], "Jita >> Amamake (10 m3)")
        self.assertEqual(row["type"], "Courier")

        # details view
        request = self.factory.get(
            reverse(
                "memberaudit:character_contract_details",
                args=[self.character.pk, contract.pk],
            )
        )
        request.user = self.user
        response = character_contract_details(request, self.character.pk, contract.pk)
        self.assertEqual(response.status_code, 200)

    def test_character_contract_details_error(self):
        contract_pk = generate_invalid_pk(CharacterContract)
        request = self.factory.get(
            reverse(
                "memberaudit:character_contract_details",
                args=[self.character.pk, contract_pk],
            )
        )
        request.user = self.user
        response = character_contract_details(request, self.character.pk, contract_pk)
        self.assertEqual(response.status_code, 200)
        self.assertIn("not found for character", response_text(response))

    @patch(MODULE_PATH + ".now")
    def test_items_included_data_normal(self, mock_now):
        """items exchange single item"""
        date_issued = dt.datetime(2020, 10, 8, 16, 45, tzinfo=pytz.utc)
        date_now = date_issued + dt.timedelta(days=1)
        date_expired = date_now + dt.timedelta(days=2, hours=3)
        mock_now.return_value = date_now
        contract = CharacterContract.objects.create(
            character=self.character,
            contract_id=42,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_ITEM_EXCHANGE,
            assignee=EveEntity.objects.get(id=1002),
            date_issued=date_issued,
            date_expired=date_expired,
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_IN_PROGRESS,
            start_location=self.jita_44,
            end_location=self.jita_44,
            title="Dummy info",
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=1,
            is_included=True,
            is_singleton=False,
            quantity=3,
            eve_type=self.item_type_1,
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=2,
            is_included=False,
            is_singleton=False,
            quantity=3,
            eve_type=self.item_type_2,
        )
        EveMarketPrice.objects.create(eve_type=self.item_type_1, average_price=5000000)
        request = self.factory.get(
            reverse(
                "memberaudit:character_contract_items_included_data",
                args=[self.character.pk, contract.pk],
            )
        )
        request.user = self.user
        response = character_contract_items_included_data(
            request, self.character.pk, contract.pk
        )
        self.assertEqual(response.status_code, 200)
        data = json_response_to_dict(response)

        self.assertSetEqual(set(data.keys()), {1})
        obj = data[1]
        self.assertEqual(obj["name"]["sort"], "High-grade Snake Alpha")
        self.assertEqual(obj["quantity"], 3)
        self.assertEqual(obj["group"], "Cyberimplant")
        self.assertEqual(obj["category"], "Implant")
        self.assertEqual(obj["price"], 5000000)
        self.assertEqual(obj["total"], 15000000)
        self.assertFalse(obj["is_blueprint_copy"])

    @patch(MODULE_PATH + ".now")
    def test_items_included_data_bpo(self, mock_now):
        """items exchange single item, which is an BPO"""
        date_issued = dt.datetime(2020, 10, 8, 16, 45, tzinfo=pytz.utc)
        date_now = date_issued + dt.timedelta(days=1)
        date_expired = date_now + dt.timedelta(days=2, hours=3)
        mock_now.return_value = date_now
        contract = CharacterContract.objects.create(
            character=self.character,
            contract_id=42,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_ITEM_EXCHANGE,
            assignee=EveEntity.objects.get(id=1002),
            date_issued=date_issued,
            date_expired=date_expired,
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_IN_PROGRESS,
            start_location=self.jita_44,
            end_location=self.jita_44,
            title="Dummy info",
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=1,
            is_included=True,
            is_singleton=True,
            quantity=1,
            raw_quantity=-2,
            eve_type=self.item_type_1,
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=2,
            is_included=True,
            is_singleton=False,
            quantity=3,
            eve_type=self.item_type_2,
        )
        EveMarketPrice.objects.create(eve_type=self.item_type_1, average_price=5000000)
        request = self.factory.get(
            reverse(
                "memberaudit:character_contract_items_included_data",
                args=[self.character.pk, contract.pk],
            )
        )
        request.user = self.user
        response = character_contract_items_included_data(
            request, self.character.pk, contract.pk
        )
        self.assertEqual(response.status_code, 200)
        data = json_response_to_dict(response)

        self.assertSetEqual(set(data.keys()), {1, 2})
        obj = data[1]
        self.assertEqual(obj["name"]["sort"], "High-grade Snake Alpha [BPC]")
        self.assertEqual(obj["quantity"], "")
        self.assertEqual(obj["group"], "Cyberimplant")
        self.assertEqual(obj["category"], "Implant")
        self.assertIsNone(obj["price"])
        self.assertIsNone(obj["total"])
        self.assertTrue(obj["is_blueprint_copy"])

    @patch(MODULE_PATH + ".now")
    def test_items_requested_data_normal(self, mock_now):
        """items exchange single item"""
        date_issued = dt.datetime(2020, 10, 8, 16, 45, tzinfo=pytz.utc)
        date_now = date_issued + dt.timedelta(days=1)
        date_expired = date_now + dt.timedelta(days=2, hours=3)
        mock_now.return_value = date_now
        contract = CharacterContract.objects.create(
            character=self.character,
            contract_id=42,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_ITEM_EXCHANGE,
            assignee=EveEntity.objects.get(id=1002),
            date_issued=date_issued,
            date_expired=date_expired,
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_IN_PROGRESS,
            start_location=self.jita_44,
            end_location=self.jita_44,
            title="Dummy info",
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=1,
            is_included=False,
            is_singleton=False,
            quantity=3,
            eve_type=self.item_type_1,
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=2,
            is_included=True,
            is_singleton=False,
            quantity=3,
            eve_type=self.item_type_2,
        )
        EveMarketPrice.objects.create(eve_type=self.item_type_1, average_price=5000000)
        request = self.factory.get(
            reverse(
                "memberaudit:character_contract_items_requested_data",
                args=[self.character.pk, contract.pk],
            )
        )
        request.user = self.user
        response = character_contract_items_requested_data(
            request, self.character.pk, contract.pk
        )
        self.assertEqual(response.status_code, 200)
        data = json_response_to_dict(response)

        self.assertSetEqual(set(data.keys()), {1})
        obj = data[1]
        self.assertEqual(obj["name"]["sort"], "High-grade Snake Alpha")
        self.assertEqual(obj["quantity"], 3)
        self.assertEqual(obj["group"], "Cyberimplant")
        self.assertEqual(obj["category"], "Implant")
        self.assertEqual(obj["price"], 5000000)
        self.assertEqual(obj["total"], 15000000)
        self.assertFalse(obj["is_blueprint_copy"])


class TestViewsOther(LoadTestDataMixin, TestCase):
    def test_can_open_index_view(self):
        request = self.factory.get(reverse("memberaudit:index"))
        request.user = self.user
        response = index(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("memberaudit:launcher"))

    def test_can_open_launcher_view_1(self):
        """user with main"""
        request = self.factory.get(reverse("memberaudit:launcher"))
        request.user = self.user
        response = launcher(request)
        self.assertEqual(response.status_code, 200)

    def test_can_open_launcher_view_2(self):
        """user without main"""
        user = AuthUtils.create_user("John Doe")
        user = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.basic_access", user
        )

        request = self.factory.get(reverse("memberaudit:launcher"))
        request.user = user
        response = launcher(request)
        self.assertEqual(response.status_code, 200)

    def test_can_open_character_main_view(self):
        request = self.factory.get(
            reverse("memberaudit:character_viewer", args=[self.character.pk])
        )
        request.user = self.user
        response = character_viewer(request, self.character.pk)
        self.assertEqual(response.status_code, 200)

    def test_can_open_character_finder_view(self):
        self.user = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.finder_access", self.user
        )
        request = self.factory.get(reverse("memberaudit:character_finder"))
        request.user = self.user
        response = character_finder(request)
        self.assertEqual(response.status_code, 200)

    def test_character_finder_data(self):
        self.user = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.finder_access", self.user
        )
        CharacterLocation.objects.create(
            character=self.character, eve_solar_system=self.jita, location=self.jita_44
        )
        character_1002 = add_memberaudit_character_to_user(self.user, 1002)

        request = self.factory.get(reverse("memberaudit:character_finder_data"))
        request.user = self.user
        response = character_finder_data(request)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertSetEqual(
            {x["character_pk"] for x in data}, {self.character.pk, character_1002.pk}
        )

    def test_can_open_reports_view(self):
        self.user = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.reports_access", self.user
        )
        request = self.factory.get(reverse("memberaudit:reports"))
        request.user = self.user
        response = reports(request)
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

    @patch(MODULE_PATH + ".data_exporters.default_destination")
    def test_should_return_export_file(self, mock_default_destination):
        with TemporaryDirectory() as tmpdirname:
            # given
            contract_item_file = Path(tmpdirname) / "memberaudit_contract-item.zip"
            with contract_item_file.open(mode="w") as _:
                pass
            mock_default_destination.return_value = Path(tmpdirname)
            user, _ = create_user_from_evecharacter(
                1122,
                permissions=["memberaudit.basic_access", "memberaudit.exports_access"],
            )
            request = self.factory.get(
                reverse("memberaudit:download_export_file", args=["contract-item"])
            )
            request.user = user
            # when
            response = download_export_file(request, "contract-item")
            # then
            self.assertEqual(response.status_code, 200)

    @patch(MODULE_PATH + ".data_exporters.default_destination")
    def test_should_raise_404_when_export_file_not_found(
        self, mock_default_destination
    ):
        with TemporaryDirectory() as tmpdirname:
            # given
            mock_default_destination.return_value = Path(tmpdirname)
            user, _ = create_user_from_evecharacter(
                1122,
                permissions=["memberaudit.basic_access", "memberaudit.exports_access"],
            )
            request = self.factory.get(
                reverse("memberaudit:download_export_file", args=["contract-item"])
            )
            request.user = user
            # when/then
            with self.assertRaises(Http404):
                download_export_file(request, "contract-item")

    @patch(MODULE_PATH + ".messages")
    @patch(MODULE_PATH + ".tasks.export_data_for_topic")
    def test_should_start_export_task(
        self, mock_task_export_data_for_topic, mock_messages_plus
    ):
        # given
        user, _ = create_user_from_evecharacter(
            1122, permissions=["memberaudit.basic_access", "memberaudit.exports_access"]
        )
        request = self.factory.get(
            reverse("memberaudit:data_export_run_update", args=["contract-item"])
        )
        request.user = user
        # when
        response = data_export_run_update(request, "contract-item")
        # then
        self.assertEqual(response.status_code, 302)
        self.assertTrue(mock_task_export_data_for_topic.delay.called)
        _, kwargs = mock_task_export_data_for_topic.delay.call_args
        self.assertEqual(kwargs["topic"], "contract-item")
        self.assertEqual(kwargs["user_pk"], user.pk)
        self.assertTrue(mock_messages_plus.info.called)


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
