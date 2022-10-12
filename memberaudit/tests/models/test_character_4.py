import datetime as dt
from unittest.mock import patch

from django.test import TestCase
from django.utils.dateparse import parse_datetime
from eveuniverse.models import EveSolarSystem, EveType

from allianceauth.eveonline.models import EveCharacter
from allianceauth.tests.auth_utils import AuthUtils
from app_utils.esi_testing import EsiClientStub, EsiEndpoint
from app_utils.testing import NoSocketsTestCase, create_user_from_evecharacter

from ...models import CharacterAttributes
from ..testdata.esi_client_stub import esi_client_stub
from ..testdata.factories import create_character, create_character_mining_ledger_entry
from ..testdata.load_entities import load_entities
from ..testdata.load_eveuniverse import load_eveuniverse
from ..utils import (
    add_memberaudit_character_to_user,
    create_memberaudit_character,
    create_user_from_evecharacter_with_access,
)
from .utils import CharacterUpdateTestDataMixin

MODELS_PATH = "memberaudit.models"
MANAGERS_PATH = "memberaudit.managers"
TASKS_PATH = "memberaudit.tasks"


class TestCharacterUserHasAccess(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_entities()

    def test_user_owning_character_has_access(self):
        # given
        character_1001 = create_memberaudit_character(1001)
        user = character_1001.eve_character.character_ownership.user
        # when/then
        self.assertTrue(character_1001.user_has_access(user))

    def test_other_user_has_no_access(self):
        # given
        character_1001 = create_memberaudit_character(1001)
        user = AuthUtils.create_user("Lex Luthor")
        # when/then
        self.assertFalse(character_1001.user_has_access(user))

    def test_has_no_access_for_view_everything_without_scope_permission(self):
        # given
        character_1001 = create_memberaudit_character(1101)
        user, _ = create_user_from_evecharacter(
            1001,
            permissions=["memberaudit.basic_access", "memberaudit.view_everything"],
        )
        # when/then
        self.assertFalse(character_1001.user_has_access(user))

    def test_has_access_for_view_everything_with_scope_permission(self):
        # given
        character_1001 = create_memberaudit_character(1001)
        user, _ = create_user_from_evecharacter(
            1002,
            permissions=[
                "memberaudit.basic_access",
                "memberaudit.view_everything",
                "memberaudit.characters_access",
            ],
        )
        # when/then
        self.assertTrue(character_1001.user_has_access(user))

    def test_has_access_for_view_everything_with_scope_permission_to_orphan(self):
        # given
        character_1121 = create_character(EveCharacter.objects.get(character_id=1121))
        user, _ = create_user_from_evecharacter(
            1002,
            permissions=[
                "memberaudit.basic_access",
                "memberaudit.view_everything",
                "memberaudit.characters_access",
            ],
        )
        # when/then
        self.assertTrue(character_1121.user_has_access(user))

    def test_view_same_corporation_1a(self):
        """
        when user has view_same_corporation permission and not characters_access
        and is in the same corporation as the character owner (main)
        then return False
        """
        # given
        character_1001 = create_memberaudit_character(1001)
        user, _ = create_user_from_evecharacter(
            1002,
            permissions=[
                "memberaudit.basic_access",
                "memberaudit.view_same_corporation",
            ],
        )
        # when/then
        self.assertFalse(character_1001.user_has_access(user))

    def test_view_same_corporation_1b(self):
        """
        when user has view_same_corporation permission and characters_access
        and is in the same corporation as the character owner (main)
        then return True
        """
        # given
        character_1001 = create_memberaudit_character(1001)
        user_3, _ = create_user_from_evecharacter_with_access(1002)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_corporation", user_3
        )
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.characters_access", user_3
        )
        # when/then
        self.assertTrue(character_1001.user_has_access(user_3))

    def test_view_same_corporation_2a(self):
        """
        when user has view_same_corporation permission and not characters_access
        and is in the same corporation as the character owner (alt)
        then return False
        """
        # given
        character_1001 = create_memberaudit_character(1001)
        user_3, _ = create_user_from_evecharacter_with_access(1002)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_corporation", user_3
        )
        character_1103 = add_memberaudit_character_to_user(
            character_1001.eve_character.character_ownership.user, 1103
        )
        # when/then
        self.assertFalse(character_1103.user_has_access(user_3))

    def test_view_same_corporation_2b(self):
        """
        when user has view_same_corporation permission and characters_access
        and is in the same corporation as the character owner (alt)
        then return True
        """
        # given
        character_1001 = create_memberaudit_character(1001)
        user_3, _ = create_user_from_evecharacter_with_access(1002)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_corporation", user_3
        )
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.characters_access", user_3
        )
        character_1103 = add_memberaudit_character_to_user(
            character_1001.eve_character.character_ownership.user, 1103
        )
        self.assertTrue(character_1103.user_has_access(user_3))

    def test_view_same_corporation_3(self):
        """
        when user has view_same_corporation permission and characters_access
        and is NOT in the same corporation as the character owner
        then return False
        """
        # given
        character_1001 = create_memberaudit_character(1001)
        user_3, _ = create_user_from_evecharacter_with_access(1003)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_corporation", user_3
        )
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.characters_access", user_3
        )
        # when/then
        self.assertFalse(character_1001.user_has_access(user_3))

    def test_view_same_alliance_1a(self):
        """
        when user has view_same_alliance permission and not characters_access
        and is in the same alliance as the character's owner (main)
        then return False
        """
        # given
        character_1001 = create_memberaudit_character(1001)
        user_3, _ = create_user_from_evecharacter_with_access(1003)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_alliance", user_3
        )
        # when/then
        self.assertFalse(character_1001.user_has_access(user_3))

    def test_view_same_alliance_1b(self):
        """
        when user has view_same_alliance permission and characters_access
        and is in the same alliance as the character's owner (main)
        then return True
        """
        # given
        character_1001 = create_memberaudit_character(1001)
        user_3, _ = create_user_from_evecharacter_with_access(1003)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_alliance", user_3
        )
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.characters_access", user_3
        )
        # when/then
        self.assertTrue(character_1001.user_has_access(user_3))

    def test_view_same_alliance_2a(self):
        """
        when user has view_same_alliance permission and not characters_access
        and is in the same alliance as the character's owner (alt)
        then return False
        """
        # given
        character_1001 = create_memberaudit_character(1001)
        user_3, _ = create_user_from_evecharacter_with_access(1003)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_alliance", user_3
        )
        character_1103 = add_memberaudit_character_to_user(
            character_1001.eve_character.character_ownership.user, 1103
        )
        # when/then
        self.assertFalse(character_1103.user_has_access(user_3))

    def test_view_same_alliance_2b(self):
        """
        when user has view_same_alliance permission and characters_access
        and is in the same alliance as the character's owner (alt)
        then return True
        """
        # given
        character_1001 = create_memberaudit_character(1001)
        user_3, _ = create_user_from_evecharacter_with_access(1003)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_alliance", user_3
        )
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.characters_access", user_3
        )
        character_1103 = add_memberaudit_character_to_user(
            character_1001.eve_character.character_ownership.user, 1103
        )
        # when/then
        self.assertTrue(character_1103.user_has_access(user_3))

    def test_view_same_alliance_3(self):
        """
        when user has view_same_alliance permission and characters_access
        and is NOT in the same alliance as the character owner
        then return False
        """
        # given
        character_1001 = create_memberaudit_character(1001)
        user_3, _ = create_user_from_evecharacter_with_access(1101)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_alliance", user_3
        )
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.characters_access", user_3
        )
        # when/then
        self.assertFalse(character_1001.user_has_access(user_3))

    def test_recruiter_access_1(self):
        """
        when user has recruiter permission
        and character is shared
        then return True
        """
        # given
        character_1001 = create_memberaudit_character(1001)
        character_1001.is_shared = True
        character_1001.save()
        AuthUtils.add_permission_to_user_by_name(
            "memberaudit.share_characters",
            character_1001.eve_character.character_ownership.user,
        )
        user_3, _ = create_user_from_evecharacter_with_access(1101)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_shared_characters", user_3
        )
        # when/then
        self.assertTrue(character_1001.user_has_access(user_3))

    def test_recruiter_access_2(self):
        """
        when user has recruiter permission
        and character is NOT shared
        then return False
        """
        # given
        character_1001 = create_memberaudit_character(1001)
        character_1001.is_shared = False
        character_1001.save()
        AuthUtils.add_permission_to_user_by_name(
            "memberaudit.share_characters",
            character_1001.eve_character.character_ownership.user,
        )
        user_3, _ = create_user_from_evecharacter_with_access(1101)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_shared_characters", user_3
        )
        # when/then
        self.assertFalse(character_1001.user_has_access(user_3))


@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateAttributes(CharacterUpdateTestDataMixin, NoSocketsTestCase):
    def test_create(self, mock_esi):
        """can load attributes from test data"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_attributes()
        self.assertEqual(
            self.character_1001.attributes.accrued_remap_cooldown_date,
            parse_datetime("2016-10-24T09:00:00Z"),
        )

        self.assertEqual(
            self.character_1001.attributes.last_remap_date,
            parse_datetime("2016-10-24T09:00:00Z"),
        )

        self.assertEqual(self.character_1001.attributes.charisma, 16)
        self.assertEqual(self.character_1001.attributes.intelligence, 17)
        self.assertEqual(self.character_1001.attributes.memory, 18)
        self.assertEqual(self.character_1001.attributes.perception, 19)
        self.assertEqual(self.character_1001.attributes.willpower, 20)

    def test_update(self, mock_esi):
        """can create attributes from scratch"""
        mock_esi.client = esi_client_stub

        CharacterAttributes.objects.create(
            character=self.character_1001,
            accrued_remap_cooldown_date="2020-10-24T09:00:00Z",
            last_remap_date="2020-10-24T09:00:00Z",
            bonus_remaps=4,
            charisma=102,
            intelligence=103,
            memory=104,
            perception=105,
            willpower=106,
        )

        self.character_1001.update_attributes()
        self.character_1001.attributes.refresh_from_db()

        self.assertEqual(
            self.character_1001.attributes.accrued_remap_cooldown_date,
            parse_datetime("2016-10-24T09:00:00Z"),
        )

        self.assertEqual(
            self.character_1001.attributes.last_remap_date,
            parse_datetime("2016-10-24T09:00:00Z"),
        )

        self.assertEqual(self.character_1001.attributes.charisma, 16)
        self.assertEqual(self.character_1001.attributes.intelligence, 17)
        self.assertEqual(self.character_1001.attributes.memory, 18)
        self.assertEqual(self.character_1001.attributes.perception, 19)
        self.assertEqual(self.character_1001.attributes.willpower, 20)


@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateMiningLedger(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_eveuniverse()
        load_entities()
        cls.character_1001 = create_memberaudit_character(1001)
        cls.endpoints = [
            EsiEndpoint(
                "Industry",
                "get_characters_character_id_mining",
                "character_id",
                needs_token=True,
                data={
                    "1001": [
                        {
                            "date": "2017-09-19",
                            "quantity": 7004,
                            "solar_system_id": 30002537,
                            "type_id": 17471,
                        },
                        {
                            "date": "2017-09-18",
                            "quantity": 5199,
                            "solar_system_id": 30002537,
                            "type_id": 17471,
                        },
                    ]
                },
            ),
        ]
        cls.esi_client_stub = EsiClientStub.create_from_endpoints(cls.endpoints)

    def test_should_add_new_entry_from_scratch(self, mock_esi):
        # given
        mock_esi.client = self.esi_client_stub
        # when
        with patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None):
            self.character_1001.update_mining_ledger()
        # then
        self.assertEqual(self.character_1001.mining_ledger.count(), 2)
        obj = self.character_1001.mining_ledger.first()
        self.assertEqual(obj.date, dt.date(2017, 9, 19))
        self.assertEqual(obj.eve_type, EveType.objects.get(name="Dense Veldspar"))
        self.assertEqual(
            obj.eve_solar_system, EveSolarSystem.objects.get(name="Amamake")
        )
        self.assertEqual(obj.quantity, 7004)

    def test_should_update_existing_entries(self, mock_esi):
        # given
        mock_esi.client = self.esi_client_stub
        create_character_mining_ledger_entry(
            character=self.character_1001,
            date=dt.date(2017, 9, 19),
            eve_solar_system=EveSolarSystem.objects.get(name="Amamake"),
            eve_type=EveType.objects.get(name="Dense Veldspar"),
            quantity=5,
        )
        # when
        with patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None):
            self.character_1001.update_mining_ledger()
        # then
        self.assertEqual(self.character_1001.mining_ledger.count(), 2)
        obj = self.character_1001.mining_ledger.get(
            date=dt.date(2017, 9, 19),
            eve_solar_system=EveSolarSystem.objects.get(name="Amamake"),
            eve_type=EveType.objects.get(name="Dense Veldspar"),
        )
        self.assertEqual(obj.quantity, 7004)
