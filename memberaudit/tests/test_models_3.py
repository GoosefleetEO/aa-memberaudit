import datetime as dt
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from eveuniverse.models import EveSolarSystem

from allianceauth.tests.auth_utils import AuthUtils
from app_utils.testing import NoSocketsTestCase, queryset_pks

from ..models import General, Location, MailEntity
from ..models.character import data_retention_cutoff
from .testdata.load_entities import load_entities
from .testdata.load_eveuniverse import load_eveuniverse
from .testdata.load_locations import load_locations
from .utils import (
    add_memberaudit_character_to_user,
    create_memberaudit_character,
    create_user_from_evecharacter_with_access,
)

MODELS_PATH = "memberaudit.models"
MANAGERS_PATH = "memberaudit.managers"
TASKS_PATH = "memberaudit.tasks"


class TestCharacterUserHasAccess(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_entities()

    def setUp(self) -> None:
        self.character_1001 = create_memberaudit_character(1001)

    def test_user_owning_character_has_access(self):
        """
        when user is the owner of the character
        then return True
        """
        self.assertTrue(
            self.character_1001.user_has_access(
                self.character_1001.character_ownership.user
            )
        )

    def test_other_user_has_no_access(self):
        """
        when user is not the owner of the character
        and has no special permissions
        then return False
        """
        user_2 = AuthUtils.create_user("Lex Luthor")
        self.assertFalse(self.character_1001.user_has_access(user_2))

    def test_view_everything_1(self):
        """
        when user has view_everything permission and not characters_access
        then return False
        """
        user_3 = AuthUtils.create_user("Peter Parker")
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_everything", user_3
        )
        self.assertFalse(self.character_1001.user_has_access(user_3))

    def test_view_everything_2(self):
        """
        when user has view_everything permission and characters_access
        then return True
        """
        user_3 = AuthUtils.create_user("Peter Parker")
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_everything", user_3
        )
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.characters_access", user_3
        )
        self.assertTrue(self.character_1001.user_has_access(user_3))

    def test_view_same_corporation_1a(self):
        """
        when user has view_same_corporation permission and not characters_access
        and is in the same corporation as the character owner (main)
        then return False
        """
        user_3, _ = create_user_from_evecharacter_with_access(1002)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_corporation", user_3
        )
        self.assertFalse(self.character_1001.user_has_access(user_3))

    def test_view_same_corporation_1b(self):
        """
        when user has view_same_corporation permission and characters_access
        and is in the same corporation as the character owner (main)
        then return True
        """
        user_3, _ = create_user_from_evecharacter_with_access(1002)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_corporation", user_3
        )
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.characters_access", user_3
        )
        self.assertTrue(self.character_1001.user_has_access(user_3))

    def test_view_same_corporation_2a(self):
        """
        when user has view_same_corporation permission and not characters_access
        and is in the same corporation as the character owner (alt)
        then return False
        """
        user_3, _ = create_user_from_evecharacter_with_access(1002)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_corporation", user_3
        )
        character_1103 = add_memberaudit_character_to_user(
            self.character_1001.character_ownership.user, 1103
        )
        self.assertFalse(character_1103.user_has_access(user_3))

    def test_view_same_corporation_2b(self):
        """
        when user has view_same_corporation permission and characters_access
        and is in the same corporation as the character owner (alt)
        then return True
        """
        user_3, _ = create_user_from_evecharacter_with_access(1002)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_corporation", user_3
        )
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.characters_access", user_3
        )
        character_1103 = add_memberaudit_character_to_user(
            self.character_1001.character_ownership.user, 1103
        )
        self.assertTrue(character_1103.user_has_access(user_3))

    def test_view_same_corporation_3(self):
        """
        when user has view_same_corporation permission and characters_access
        and is NOT in the same corporation as the character owner
        then return False
        """

        user_3, _ = create_user_from_evecharacter_with_access(1003)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_corporation", user_3
        )
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.characters_access", user_3
        )
        self.assertFalse(self.character_1001.user_has_access(user_3))

    def test_view_same_alliance_1a(self):
        """
        when user has view_same_alliance permission and not characters_access
        and is in the same alliance as the character's owner (main)
        then return False
        """

        user_3, _ = create_user_from_evecharacter_with_access(1003)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_alliance", user_3
        )
        self.assertFalse(self.character_1001.user_has_access(user_3))

    def test_view_same_alliance_1b(self):
        """
        when user has view_same_alliance permission and characters_access
        and is in the same alliance as the character's owner (main)
        then return True
        """

        user_3, _ = create_user_from_evecharacter_with_access(1003)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_alliance", user_3
        )
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.characters_access", user_3
        )
        self.assertTrue(self.character_1001.user_has_access(user_3))

    def test_view_same_alliance_2a(self):
        """
        when user has view_same_alliance permission and not characters_access
        and is in the same alliance as the character's owner (alt)
        then return False
        """

        user_3, _ = create_user_from_evecharacter_with_access(1003)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_alliance", user_3
        )
        character_1103 = add_memberaudit_character_to_user(
            self.character_1001.character_ownership.user, 1103
        )
        self.assertFalse(character_1103.user_has_access(user_3))

    def test_view_same_alliance_2b(self):
        """
        when user has view_same_alliance permission and characters_access
        and is in the same alliance as the character's owner (alt)
        then return True
        """

        user_3, _ = create_user_from_evecharacter_with_access(1003)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_alliance", user_3
        )
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.characters_access", user_3
        )
        character_1103 = add_memberaudit_character_to_user(
            self.character_1001.character_ownership.user, 1103
        )
        self.assertTrue(character_1103.user_has_access(user_3))

    def test_view_same_alliance_3(self):
        """
        when user has view_same_alliance permission and characters_access
        and is NOT in the same alliance as the character owner
        then return False
        """
        user_3, _ = create_user_from_evecharacter_with_access(1101)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_alliance", user_3
        )
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.characters_access", user_3
        )
        self.assertFalse(self.character_1001.user_has_access(user_3))

    def test_recruiter_access_1(self):
        """
        when user has recruiter permission
        and character is shared
        then return True
        """
        self.character_1001.is_shared = True
        self.character_1001.save()
        AuthUtils.add_permission_to_user_by_name(
            "memberaudit.share_characters", self.character_1001.character_ownership.user
        )
        user_3, _ = create_user_from_evecharacter_with_access(1101)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_shared_characters", user_3
        )
        self.assertTrue(self.character_1001.user_has_access(user_3))

    def test_recruiter_access_2(self):
        """
        when user has recruiter permission
        and character is NOT shared
        then return False
        """
        self.character_1001.is_shared = False
        self.character_1001.save()
        AuthUtils.add_permission_to_user_by_name(
            "memberaudit.share_characters", self.character_1001.character_ownership.user
        )
        user_3, _ = create_user_from_evecharacter_with_access(1101)
        user_3 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_shared_characters", user_3
        )
        self.assertFalse(self.character_1001.user_has_access(user_3))


class TestMailEntity(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_entities()

    def test_str(self):
        obj, _ = MailEntity.objects.update_or_create_from_eve_entity_id(1001)
        self.assertEqual(str(obj), "Bruce Wayne")

    def test_repr(self):
        obj, _ = MailEntity.objects.update_or_create_from_eve_entity_id(1001)
        self.assertEqual(
            repr(obj), "MailEntity(id=1001, category=CH, name='Bruce Wayne')"
        )

    def test_eve_entity_categories(self):
        obj, _ = MailEntity.objects.update_or_create_from_eve_entity_id(1001)
        self.assertSetEqual(
            obj.eve_entity_categories,
            {
                MailEntity.Category.ALLIANCE,
                MailEntity.Category.CHARACTER,
                MailEntity.Category.CORPORATION,
            },
        )

    def test_name_plus_1(self):
        obj, _ = MailEntity.objects.update_or_create_from_eve_entity_id(1001)
        self.assertEqual(obj.name_plus, "Bruce Wayne")

    def test_name_plus_2(self):
        obj = MailEntity.objects.create(id=42, category=MailEntity.Category.ALLIANCE)
        self.assertEqual(obj.name_plus, "Alliance #42")

    def test_need_to_specify_category(self):
        with self.assertRaises(ValidationError):
            MailEntity.objects.create(id=1)

    def test_url_1(self):
        obj, _ = MailEntity.objects.update_or_create_from_eve_entity_id(3001)
        self.assertIn("dotlan", obj.external_url())

    def test_url_2(self):
        obj, _ = MailEntity.objects.update_or_create_from_eve_entity_id(2001)
        self.assertIn("dotlan", obj.external_url())

    def test_url_3(self):
        obj, _ = MailEntity.objects.update_or_create_from_eve_entity_id(1001)
        self.assertIn("evewho", obj.external_url())

    def test_url_4(self):
        obj = MailEntity.objects.create(
            id=42, category=MailEntity.Category.MAILING_LIST, name="Dummy"
        )
        self.assertEqual(obj.external_url(), "")

    def test_url_5(self):
        obj = MailEntity.objects.create(id=9887, category=MailEntity.Category.ALLIANCE)
        self.assertEqual(obj.external_url(), "")

    def test_url_6(self):
        obj = MailEntity.objects.create(
            id=9887, category=MailEntity.Category.CORPORATION
        )
        self.assertEqual(obj.external_url(), "")


class TestGeneralUserHasAccess(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()
        load_entities()
        cls.character_1002 = create_memberaudit_character(1002)
        cls.user_1002 = cls.character_1002.character_ownership.user
        cls.character_1003 = create_memberaudit_character(1003)
        cls.user_1003 = cls.character_1003.character_ownership.user
        cls.character_1101 = create_memberaudit_character(1101)
        cls.user_1101 = cls.character_1101.character_ownership.user
        cls.user_dummy = AuthUtils.create_user("No-access-to-Member-Audit")

    def setUp(self) -> None:
        self.character_1001 = create_memberaudit_character(1001)
        self.user_1001 = self.character_1001.character_ownership.user

    def test_should_see_own_user_only(self):
        # when
        result = General.accessible_users(user=self.user_1001)
        # then
        self.assertSetEqual(queryset_pks(result), {self.user_1001.pk})

    def test_should_see_all_memberaudit_users(self):
        # given
        self.user_1001 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_everything", self.user_1001
        )
        # when
        result = General.accessible_users(user=self.user_1001)
        # then
        self.assertSetEqual(
            queryset_pks(result),
            {
                self.user_1001.pk,
                self.user_1002.pk,
                self.user_1003.pk,
                self.user_1101.pk,
            },
        )

    def test_should_see_own_alliance_only(self):
        # given
        self.user_1001 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_alliance", self.user_1001
        )
        # when
        result = General.accessible_users(user=self.user_1001)
        # then
        self.assertSetEqual(
            queryset_pks(result),
            {self.user_1001.pk, self.user_1002.pk, self.user_1003.pk},
        )

    def test_should_see_own_corporation_only(self):
        # given
        self.user_1001 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_corporation", self.user_1001
        )
        # when
        result = General.accessible_users(user=self.user_1001)
        # then
        self.assertSetEqual(
            queryset_pks(result),
            {self.user_1001.pk, self.user_1002.pk},
        )


class TestDataRetentionCutoff(TestCase):
    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", 10)
    def test_limit_is_set(self):
        with patch(MODELS_PATH + ".character.now") as mock_now:
            mock_now.return_value = dt.datetime(2020, 12, 19, 16, 15)
            self.assertEqual(data_retention_cutoff(), dt.datetime(2020, 12, 9, 16, 0))

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    def test_limit_not_set(self):
        with patch(MODELS_PATH + ".character.now") as mock_now:
            mock_now.return_value = dt.datetime(2020, 12, 19, 16, 15)
            self.assertIsNone(data_retention_cutoff())


class TestLocation(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()
        load_entities()
        load_locations()

    def test_str(self):
        location = Location.objects.get(id=1000000000001)
        self.assertEqual(str(location), "Amamake - Test Structure Alpha")

    def test_repr(self):
        location = Location.objects.get(id=1000000000001)
        self.assertEqual(
            repr(location),
            "Location(id=1000000000001, name='Amamake - Test Structure Alpha')",
        )

    def test_is_solar_system(self):
        location = Location.objects.create(
            id=30000142, eve_solar_system=EveSolarSystem.objects.get(id=30000142)
        )
        self.assertTrue(location.is_solar_system)
        self.assertFalse(location.is_station)
        self.assertFalse(location.is_structure)

    def test_is_station(self):
        location = Location.objects.get(id=60003760)
        self.assertFalse(location.is_solar_system)
        self.assertTrue(location.is_station)
        self.assertFalse(location.is_structure)

    def test_is_structure(self):
        location = Location.objects.get(id=1000000000001)
        self.assertFalse(location.is_solar_system)
        self.assertFalse(location.is_station)
        self.assertTrue(location.is_structure)

    def test_solar_system_url(self):
        obj_1 = Location.objects.get(id=1000000000001)
        obj_2 = Location.objects.create(id=1000000000999)

        self.assertIn("Amamake", obj_1.solar_system_url)
        self.assertEqual("", obj_2.solar_system_url)
