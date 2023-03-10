import datetime as dt
from unittest.mock import Mock, patch

from bravado.exception import HTTPForbidden, HTTPNotFound, HTTPUnauthorized

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils.timezone import now
from eveuniverse.models import EveEntity, EveSolarSystem, EveType

from allianceauth.eveonline.models import EveCorporationInfo
from allianceauth.notifications.models import Notification
from app_utils.esi import EsiStatus
from app_utils.esi_testing import BravadoResponseStub
from app_utils.testing import (
    NoSocketsTestCase,
    create_authgroup,
    create_state,
    create_user_from_evecharacter,
)

from memberaudit.models import (
    ComplianceGroupDesignation,
    Location,
    MailEntity,
    SkillSet,
)

from ..testdata.esi_client_stub import esi_client_stub
from ..testdata.factories import (
    create_compliance_group,
    create_fitting,
    create_skill,
    create_skill_plan,
    create_skill_set_group,
)
from ..testdata.load_entities import load_entities
from ..testdata.load_eveuniverse import load_eveuniverse
from ..utils import (
    add_auth_character_to_user,
    add_memberaudit_character_to_user,
    create_memberaudit_character,
)

MANAGERS_PATH = "memberaudit.managers.general"


class TestComplianceGroupDesignation(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_entities()

    def test_should_add_group_to_compliant_user_and_notify(self):
        # given
        compliance_group = create_compliance_group()
        other_group = create_authgroup(internal=True)
        user, _ = create_user_from_evecharacter(
            1001, permissions=["memberaudit.basic_access"]
        )
        add_memberaudit_character_to_user(user, 1001)
        # when
        ComplianceGroupDesignation.objects.update_user(user)
        # then
        self.assertIn(compliance_group, user.groups.all())
        self.assertNotIn(other_group, user.groups.all())
        self.assertTrue(
            user.notification_set.filter(level=Notification.Level.SUCCESS).exists()
        )

    def test_should_add_state_group_to_compliant_user_when_state_matches(self):
        # given
        member_corporation = EveCorporationInfo.objects.get(corporation_id=2001)
        my_state = create_state(member_corporations=[member_corporation], priority=200)
        compliance_group = create_compliance_group(states=[my_state])
        user, _ = create_user_from_evecharacter(
            1001, permissions=["memberaudit.basic_access"]
        )
        add_memberaudit_character_to_user(user, 1001)
        # when
        ComplianceGroupDesignation.objects.update_user(user)
        # then
        self.assertIn(compliance_group, user.groups.all())

    def test_should_not_add_state_group_to_compliant_user_when_state_not_matches(self):
        # given
        my_state = create_state(priority=200)
        compliance_group = create_compliance_group(states=[my_state])
        user, _ = create_user_from_evecharacter(
            1001, permissions=["memberaudit.basic_access"]
        )
        add_memberaudit_character_to_user(user, 1001)
        # when
        ComplianceGroupDesignation.objects.update_user(user)
        # then
        self.assertNotIn(compliance_group, user.groups.all())
        self.assertFalse(user.notification_set.exists())

    # def test_should_not_notify_if_compliant_but_no_groups_added(self):
    #     # given
    #     member_corporation = EveCorporationInfo.objects.get(corporation_id=2001)
    #     my_state = create_state(member_corporations=[member_corporation], priority=200)
    #     compliance_group = create_compliance_group(states=[my_state])
    #     user, _ = create_user_from_evecharacter(
    #         1001, permissions=["memberaudit.basic_access"]
    #     )
    #     add_memberaudit_character_to_user(user, 1001)
    #     # when
    #     ComplianceGroupDesignation.objects.update_user(user)
    #     # then
    #     self.assertIn(compliance_group, user.groups.all())

    def test_should_add_multiple_groups_to_compliant_user(self):
        # given
        compliance_group_1 = create_compliance_group()
        compliance_group_2 = create_compliance_group()
        user, _ = create_user_from_evecharacter(
            1001, permissions=["memberaudit.basic_access"]
        )
        add_memberaudit_character_to_user(user, 1001)
        # when
        ComplianceGroupDesignation.objects.update_user(user)
        # then
        self.assertIn(compliance_group_1, user.groups.all())
        self.assertIn(compliance_group_2, user.groups.all())

    def test_should_remove_group_from_non_compliant_user_and_notify(self):
        # given
        compliance_group = create_compliance_group()
        other_group = create_authgroup(internal=True)
        user, _ = create_user_from_evecharacter(
            1001, permissions=["memberaudit.basic_access"]
        )
        user.groups.add(compliance_group, other_group)
        # when
        ComplianceGroupDesignation.objects.update_user(user)
        # then
        self.assertNotIn(compliance_group, user.groups.all())
        self.assertIn(other_group, user.groups.all())
        self.assertTrue(
            user.notification_set.filter(level=Notification.Level.WARNING).exists()
        )

    def test_should_remove_multiple_groups_from_non_compliant_user(self):
        # given
        compliance_group_1 = create_compliance_group()
        compliance_group_2 = create_compliance_group()
        other_group = create_authgroup(internal=True)
        user, _ = create_user_from_evecharacter(
            1001, permissions=["memberaudit.basic_access"]
        )
        user.groups.add(compliance_group_1, compliance_group_2, other_group)
        # when
        ComplianceGroupDesignation.objects.update_user(user)
        # then
        self.assertNotIn(compliance_group_1, user.groups.all())
        self.assertNotIn(compliance_group_2, user.groups.all())
        self.assertIn(other_group, user.groups.all())

    def test_user_with_one_registered_and_one_unregistered_characater_is_not_compliant(
        self,
    ):
        # given
        compliance_group = create_compliance_group()
        user, _ = create_user_from_evecharacter(
            1001, permissions=["memberaudit.basic_access"]
        )
        add_memberaudit_character_to_user(user, 1001)
        add_auth_character_to_user(user, 1002)
        user.groups.add(compliance_group)
        # when
        ComplianceGroupDesignation.objects.update_user(user)
        # then
        self.assertNotIn(compliance_group, user.groups.all())

    def test_user_without_basic_permission_is_not_compliant(self):
        # given
        compliance_group = create_compliance_group()
        user, _ = create_user_from_evecharacter(1001)
        add_memberaudit_character_to_user(user, 1001)
        user.groups.add(compliance_group)
        # when
        ComplianceGroupDesignation.objects.update_user(user)
        # then
        self.assertNotIn(compliance_group, user.groups.all())

    def test_should_add_missing_groups_if_user_remains_compliant(self):
        # given
        compliance_group_1 = create_compliance_group()
        compliance_group_2 = create_compliance_group()
        other_group = create_authgroup(internal=True)
        user, _ = create_user_from_evecharacter(
            1001, permissions=["memberaudit.basic_access"]
        )
        add_memberaudit_character_to_user(user, 1001)
        user.groups.add(compliance_group_1)
        # when
        ComplianceGroupDesignation.objects.update_user(user)
        # then
        self.assertIn(compliance_group_1, user.groups.all())
        self.assertIn(compliance_group_2, user.groups.all())
        self.assertNotIn(other_group, user.groups.all())
        self.assertEqual(user.notification_set.count(), 0)


class TestMailEntityManager(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_entities()

    def test_get_or_create_esi_1(self):
        """When entity already exists, return it"""
        MailEntity.objects.create(
            id=1234, category=MailEntity.Category.CHARACTER, name="John Doe"
        )

        obj, created = MailEntity.objects.get_or_create_esi(id=1234)

        self.assertFalse(created)
        self.assertEqual(obj.category, MailEntity.Category.CHARACTER)
        self.assertEqual(obj.name, "John Doe")

    @patch(MANAGERS_PATH + ".fetch_esi_status")
    def test_get_or_create_esi_2(self, mock_fetch_esi_status):
        """When entity does not exist, create it from ESI / existing EveEntity"""
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)

        obj, created = MailEntity.objects.get_or_create_esi(id=1001)

        self.assertTrue(created)
        self.assertEqual(obj.category, MailEntity.Category.CHARACTER)
        self.assertEqual(obj.name, "Bruce Wayne")

    @patch(MANAGERS_PATH + ".fetch_esi_status")
    def test_update_or_create_esi_1(self, mock_fetch_esi_status):
        """When entity does not exist, create it from ESI / existing EveEntity"""
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)

        obj, created = MailEntity.objects.update_or_create_esi(id=1001)

        self.assertTrue(created)
        self.assertEqual(obj.category, MailEntity.Category.CHARACTER)
        self.assertEqual(obj.name, "Bruce Wayne")

    def test_update_or_create_esi_2(self):
        """When entity already exist and is not a mailing list,
        then update it from ESI / existing EveEntity
        """
        MailEntity.objects.create(
            id=1001, category=MailEntity.Category.CHARACTER, name="John Doe"
        )
        obj, created = MailEntity.objects.update_or_create_esi(id=1001)

        self.assertFalse(created)
        self.assertEqual(obj.category, MailEntity.Category.CHARACTER)
        self.assertEqual(obj.name, "Bruce Wayne")

    def test_update_or_create_esi_3(self):
        """When entity already exist and is a mailing list, then do nothing"""
        MailEntity.objects.create(
            id=9001, category=MailEntity.Category.MAILING_LIST, name="Dummy"
        )
        obj, created = MailEntity.objects.update_or_create_esi(id=9001)

        self.assertFalse(created)
        self.assertEqual(obj.category, MailEntity.Category.MAILING_LIST)
        self.assertEqual(obj.name, "Dummy")
        # method must not create an EveEntity object for the mailing list
        self.assertFalse(EveEntity.objects.filter(id=9001).exists())

    def test_update_or_create_from_eve_entity_1(self):
        """When entity does not exist, create it from given EveEntity"""
        eve_entity = EveEntity.objects.get(id=1001)
        obj, created = MailEntity.objects.update_or_create_from_eve_entity(eve_entity)

        self.assertTrue(created)
        self.assertEqual(obj.category, MailEntity.Category.CHARACTER)
        self.assertEqual(obj.name, "Bruce Wayne")

    def test_update_or_create_from_eve_entity_2(self):
        """When entity already exist, update it from given EveEntity"""
        MailEntity.objects.create(
            id=1001, category=MailEntity.Category.CHARACTER, name="John Doe"
        )

        eve_entity = EveEntity.objects.get(id=1001)
        obj, created = MailEntity.objects.update_or_create_from_eve_entity(eve_entity)

        self.assertFalse(created)
        self.assertEqual(obj.category, MailEntity.Category.CHARACTER)
        self.assertEqual(obj.name, "Bruce Wayne")

    def test_update_or_create_from_eve_entity_id_1(self):
        """When entity does not exist, create it from given EveEntity"""
        eve_entity = EveEntity.objects.get(id=1001)
        obj, created = MailEntity.objects.update_or_create_from_eve_entity_id(
            eve_entity.id
        )

        self.assertTrue(created)
        self.assertEqual(obj.category, MailEntity.Category.CHARACTER)
        self.assertEqual(obj.name, "Bruce Wayne")

    def test_update_or_create_from_eve_entity_id_2(self):
        """When entity already exist, update it from given EveEntity"""
        MailEntity.objects.create(
            id=1001, category=MailEntity.Category.CHARACTER, name="John Doe"
        )

        eve_entity = EveEntity.objects.get(id=1001)
        obj, created = MailEntity.objects.update_or_create_from_eve_entity_id(
            eve_entity.id
        )

        self.assertFalse(created)
        self.assertEqual(obj.category, MailEntity.Category.CHARACTER)
        self.assertEqual(obj.name, "Bruce Wayne")

    def test_bulk_resolve_1(self):
        """Can resolve all 3 categories known by EveEntity"""
        obj_1001 = MailEntity.objects.create(
            id=1001, category=MailEntity.Category.CHARACTER
        )
        obj_2001 = MailEntity.objects.create(
            id=2001, category=MailEntity.Category.CORPORATION
        )
        obj_3001 = MailEntity.objects.create(
            id=3001, category=MailEntity.Category.ALLIANCE
        )

        MailEntity.objects.bulk_update_names([obj_1001, obj_2001, obj_3001])

        self.assertEqual(obj_1001.name, "Bruce Wayne")
        self.assertEqual(obj_2001.name, "Wayne Technologies")
        self.assertEqual(obj_3001.name, "Wayne Enterprises")

    def test_bulk_resolve_2(self):
        """Will ignore categories not known to EveEntity"""

        obj_1001 = MailEntity.objects.create(
            id=1001, category=MailEntity.Category.CHARACTER
        )
        obj_9001 = MailEntity.objects.create(
            id=9001, category=MailEntity.Category.MAILING_LIST
        )
        obj_9002 = MailEntity.objects.create(
            id=9002, category=MailEntity.Category.UNKNOWN
        )

        MailEntity.objects.bulk_update_names([obj_1001, obj_9001, obj_9002])

        self.assertEqual(obj_1001.name, "Bruce Wayne")
        self.assertEqual(obj_9001.name, "")
        self.assertEqual(obj_9002.name, "")

    def test_bulk_resolve_3(self):
        """When object list is empty, then no op"""

        try:
            MailEntity.objects.bulk_update_names([])
        except Exception as ex:
            self.fail(f"Unexpected exception: {ex}")

    def test_bulk_resolve_4(self):
        """When object already has a name, then update it"""
        obj_1001 = MailEntity.objects.create(
            id=1001, category=MailEntity.Category.CHARACTER, name="John Doe"
        )

        MailEntity.objects.bulk_update_names([obj_1001])

        self.assertEqual(obj_1001.name, "Bruce Wayne")

    def test_bulk_resolve_5(self):
        """When object already has a name and respective option is chosen
        then ignore it
        """
        obj_1001 = MailEntity.objects.create(
            id=1001, category=MailEntity.Category.CHARACTER, name="John Doe"
        )

        MailEntity.objects.bulk_update_names([obj_1001], keep_names=True)

        self.assertEqual(obj_1001.name, "John Doe")


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
@patch(MANAGERS_PATH + ".fetch_esi_status")
class TestMailEntityManagerAsync(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_entities()
        MailEntity.objects.all().delete()

    def test_get_or_create_esi_async_1(self, mock_fetch_esi_status):
        """When entity already exists, return it"""
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)

        MailEntity.objects.create(
            id=1234, category=MailEntity.Category.CHARACTER, name="John Doe"
        )

        obj, created = MailEntity.objects.get_or_create_esi_async(id=1234)

        self.assertFalse(created)
        self.assertEqual(obj.category, MailEntity.Category.CHARACTER)
        self.assertEqual(obj.name, "John Doe")
        self.assertFalse(mock_fetch_esi_status.called)  # was esi error status checked

    def test_get_or_create_esi_async_2(self, mock_fetch_esi_status):
        """When entity does not exist and no category specified,
        then create it asynchronously from ESI / existing EveEntity
        """
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)

        obj, created = MailEntity.objects.get_or_create_esi_async(id=1001)

        self.assertTrue(created)
        self.assertEqual(obj.category, MailEntity.Category.UNKNOWN)
        self.assertEqual(obj.name, "")

        obj.refresh_from_db()
        self.assertEqual(obj.category, MailEntity.Category.CHARACTER)
        self.assertEqual(obj.name, "Bruce Wayne")
        self.assertTrue(mock_fetch_esi_status.called)  # was esi error status checked

    def test_get_or_create_esi_async_3(self, mock_fetch_esi_status):
        """When entity does not exist and category is not mailing list,
        then create it synchronously from ESI / existing EveEntity
        """
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)

        obj, created = MailEntity.objects.get_or_create_esi_async(
            id=1001, category=MailEntity.Category.CHARACTER
        )

        self.assertTrue(created)
        self.assertEqual(obj.category, MailEntity.Category.CHARACTER)
        self.assertEqual(obj.name, "Bruce Wayne")
        self.assertFalse(mock_fetch_esi_status.called)  # was esi error status checked

    def test_update_or_create_esi_async_1(self, mock_fetch_esi_status):
        """When entity does not exist, create empty object and run task to resolve"""
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)

        obj, created = MailEntity.objects.update_or_create_esi_async(1001)

        self.assertTrue(created)
        self.assertEqual(obj.category, MailEntity.Category.UNKNOWN)
        self.assertEqual(obj.name, "")

        obj.refresh_from_db()
        self.assertEqual(obj.category, MailEntity.Category.CHARACTER)
        self.assertEqual(obj.name, "Bruce Wayne")

        self.assertTrue(mock_fetch_esi_status.called)  # was esi error status checked

    def test_update_or_create_esi_async_2(self, mock_fetch_esi_status):
        """When entity exists and not a mailing list, then update synchronously"""
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        MailEntity.objects.create(
            id=1001, category=MailEntity.Category.CHARACTER, name="John Doe"
        )

        obj, created = MailEntity.objects.update_or_create_esi_async(1001)

        self.assertFalse(created)
        self.assertEqual(obj.category, MailEntity.Category.CHARACTER)
        self.assertEqual(obj.name, "Bruce Wayne")

        self.assertFalse(mock_fetch_esi_status.called)  # was esi error status checked

    def test_update_or_create_esi_async_3(self, mock_fetch_esi_status):
        """When entity exists and is a mailing list, then do nothing"""
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        MailEntity.objects.create(
            id=9001, category=MailEntity.Category.MAILING_LIST, name="Dummy"
        )

        obj, created = MailEntity.objects.update_or_create_esi_async(9001)

        self.assertFalse(created)
        self.assertEqual(obj.category, MailEntity.Category.MAILING_LIST)
        self.assertEqual(obj.name, "Dummy")

        self.assertFalse(mock_fetch_esi_status.called)  # was esi error status checked

    def test_update_or_create_esi_async_4(self, mock_fetch_esi_status):
        """When entity does not exist and category is not a mailing list,
        then create empty object from ESI synchronously
        """
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)

        obj, created = MailEntity.objects.update_or_create_esi_async(
            1001, MailEntity.Category.CHARACTER
        )

        self.assertTrue(created)
        self.assertEqual(obj.category, MailEntity.Category.CHARACTER)
        self.assertEqual(obj.name, "Bruce Wayne")

        self.assertFalse(mock_fetch_esi_status.called)  # was esi error status checked


@patch(MANAGERS_PATH + ".esi")
class TestLocationManager(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()
        load_entities()
        cls.jita = EveSolarSystem.objects.get(id=30000142)
        cls.amamake = EveSolarSystem.objects.get(id=30002537)
        cls.astrahus = EveType.objects.get(id=35832)
        cls.athanor = EveType.objects.get(id=35835)
        cls.jita_trade_hub = EveType.objects.get(id=52678)
        cls.corporation_2001 = EveEntity.objects.get(id=2001)
        cls.corporation_2002 = EveEntity.objects.get(id=2002)
        cls.character = create_memberaudit_character(1001)
        cls.token = (
            cls.character.eve_character.character_ownership.user.token_set.first()
        )

    # Structures

    @patch(MANAGERS_PATH + ".fetch_esi_status")
    def test_can_create_structure(self, mock_fetch_esi_status, mock_esi):
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        mock_esi.client = esi_client_stub

        obj, created = Location.objects.update_or_create_esi(
            id=1000000000001, token=self.token
        )
        self.assertTrue(created)
        self.assertEqual(obj.id, 1000000000001)
        self.assertEqual(obj.name, "Amamake - Test Structure Alpha")
        self.assertEqual(obj.eve_solar_system, self.amamake)
        self.assertEqual(obj.eve_type, self.astrahus)
        self.assertEqual(obj.owner, self.corporation_2001)

    @patch(MANAGERS_PATH + ".fetch_esi_status")
    def test_can_update_structure(self, mock_fetch_esi_status, mock_esi):
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        mock_esi.client = esi_client_stub

        obj, _ = Location.objects.update_or_create_esi(
            id=1000000000001, token=self.token
        )
        obj.name = "Not my structure"
        obj.eve_solar_system = self.jita
        obj.eve_type = self.jita_trade_hub
        obj.owner = self.corporation_2002
        obj.save()
        obj, created = Location.objects.update_or_create_esi(
            id=1000000000001, token=self.token
        )
        self.assertFalse(created)
        self.assertEqual(obj.id, 1000000000001)
        self.assertEqual(obj.name, "Amamake - Test Structure Alpha")
        self.assertEqual(obj.eve_solar_system, self.amamake)
        self.assertEqual(obj.eve_type, self.astrahus)
        self.assertEqual(obj.owner, self.corporation_2001)

    @patch(MANAGERS_PATH + ".fetch_esi_status")
    def test_does_not_update_existing_location_during_grace_period(
        self, mock_fetch_esi_status, mock_esi
    ):
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        mock_esi.client = esi_client_stub

        obj_existing = Location.objects.create(
            id=1000000000001,
            name="Existing Structure",
            eve_solar_system=self.jita,
            eve_type=self.jita_trade_hub,
            owner=self.corporation_2002,
        )
        obj, created = Location.objects.get_or_create_esi(
            id=1000000000001, token=self.token
        )
        self.assertFalse(created)
        self.assertEqual(obj, obj_existing)

    @patch(MANAGERS_PATH + ".fetch_esi_status")
    def test_always_update_existing_empty_locations_after_grace_period_1(
        self, mock_fetch_esi_status, mock_esi
    ):
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        mock_esi.client = esi_client_stub

        Location.objects.create(id=1000000000001)
        obj, _ = Location.objects.get_or_create_esi(id=1000000000001, token=self.token)
        self.assertIsNone(obj.eve_solar_system)

    @patch(MANAGERS_PATH + ".fetch_esi_status")
    def test_always_update_existing_empty_locations_after_grace_period_2(
        self, mock_fetch_esi_status, mock_esi
    ):
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        mock_esi.client = esi_client_stub

        mocked_update_at = now() - dt.timedelta(minutes=6)
        with patch("django.utils.timezone.now", Mock(return_value=mocked_update_at)):
            Location.objects.create(id=1000000000001)
            obj, _ = Location.objects.get_or_create_esi(
                id=1000000000001, token=self.token
            )
        self.assertEqual(obj.eve_solar_system, self.amamake)

    @patch(MANAGERS_PATH + ".fetch_esi_status")
    @patch(MANAGERS_PATH + ".MEMBERAUDIT_LOCATION_STALE_HOURS", 24)
    def test_always_update_existing_locations_which_are_stale(
        self, mock_fetch_esi_status, mock_esi
    ):
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        mock_esi.client = esi_client_stub

        mocked_update_at = now() - dt.timedelta(hours=25)
        with patch("django.utils.timezone.now", Mock(return_value=mocked_update_at)):
            Location.objects.create(
                id=1000000000001,
                name="Existing Structure",
                eve_solar_system=self.jita,
                eve_type=self.jita_trade_hub,
                owner=self.corporation_2002,
            )
        obj, created = Location.objects.get_or_create_esi(
            id=1000000000001, token=self.token
        )
        self.assertFalse(created)
        self.assertEqual(obj.eve_solar_system, self.amamake)

    @patch(MANAGERS_PATH + ".fetch_esi_status")
    def test_propagates_http_error_on_structure_create(
        self, mock_fetch_esi_status, mock_esi
    ):
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        mock_esi.client = esi_client_stub

        with self.assertRaises(HTTPNotFound):
            Location.objects.update_or_create_esi(id=1000000000099, token=self.token)

    @patch(MANAGERS_PATH + ".fetch_esi_status")
    def test_always_creates_empty_location_for_invalid_ids(
        self, mock_fetch_esi_status, mock_esi
    ):
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        mock_esi.client = esi_client_stub

        obj, created = Location.objects.update_or_create_esi(
            id=80000000, token=self.token
        )
        self.assertTrue(created)
        self.assertTrue(obj.is_empty)

    @patch(MANAGERS_PATH + ".fetch_esi_status")
    def test_propagates_exceptions_on_structure_create(
        self, mock_fetch_esi_status, mock_esi
    ):
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        mock_esi.client.Universe.get_universe_structures_structure_id.side_effect = (
            RuntimeError
        )

        with self.assertRaises(RuntimeError):
            Location.objects.update_or_create_esi(id=1000000000099, token=self.token)

    @patch(MANAGERS_PATH + ".fetch_esi_status")
    def test_can_create_empty_location_on_access_error_1(
        self, mock_fetch_esi_status, mock_esi
    ):
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        mock_esi.client.Universe.get_universe_structures_structure_id.side_effect = (
            HTTPForbidden(response=BravadoResponseStub(403, "Test exception"))
        )

        obj, created = Location.objects.update_or_create_esi(
            id=1000000000099, token=self.token
        )
        self.assertTrue(created)
        self.assertEqual(obj.id, 1000000000099)

    @patch(MANAGERS_PATH + ".fetch_esi_status")
    def test_can_create_empty_location_on_access_error_2(
        self, mock_fetch_esi_status, mock_esi
    ):
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        mock_esi.client.Universe.get_universe_structures_structure_id.side_effect = (
            HTTPUnauthorized(response=BravadoResponseStub(401, "Test exception"))
        )

        obj, created = Location.objects.update_or_create_esi(
            id=1000000000099, token=self.token
        )
        self.assertTrue(created)
        self.assertEqual(obj.id, 1000000000099)

    @patch(MANAGERS_PATH + ".fetch_esi_status")
    def test_does_not_creates_empty_location_on_access_errors_if_requested(
        self, mock_fetch_esi_status, mock_esi
    ):
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        mock_esi.client.Universe.get_universe_structures_structure_id.side_effect = (
            RuntimeError
        )
        with self.assertRaises(RuntimeError):
            Location.objects.update_or_create_esi(id=1000000000099, token=self.token)

    @patch(MANAGERS_PATH + ".fetch_esi_status")
    def test_records_esi_error_on_access_error(self, mock_fetch_esi_status, mock_esi):
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        mock_esi.client.Universe.get_universe_structures_structure_id.side_effect = (
            HTTPForbidden(
                response=BravadoResponseStub(
                    403,
                    "Test exception",
                    headers={
                        "X-Esi-Error-Limit-Remain": "40",
                        "X-Esi-Error-Limit-Reset": "30",
                    },
                )
            )
        )

        obj, created = Location.objects.update_or_create_esi(
            id=1000000000099, token=self.token
        )
        self.assertTrue(created)

    # Stations

    def test_can_create_station(self, mock_esi):
        mock_esi.client = esi_client_stub

        obj, created = Location.objects.update_or_create_esi(
            id=60003760, token=self.token
        )
        self.assertTrue(created)
        self.assertEqual(obj.id, 60003760)
        self.assertEqual(obj.name, "Jita IV - Moon 4 - Caldari Navy Assembly Plant")
        self.assertEqual(obj.eve_solar_system, self.jita)
        self.assertEqual(obj.eve_type, self.jita_trade_hub)
        self.assertEqual(obj.owner, self.corporation_2002)

    def test_can_update_station(self, mock_esi):
        mock_esi.client = esi_client_stub

        obj, created = Location.objects.update_or_create_esi(
            id=60003760, token=self.token
        )
        obj.name = "Not my station"
        obj.eve_solar_system = self.amamake
        obj.eve_type = self.astrahus
        obj.owner = self.corporation_2001
        obj.save()

        obj, created = Location.objects.update_or_create_esi(
            id=60003760, token=self.token
        )
        self.assertFalse(created)
        self.assertEqual(obj.id, 60003760)
        self.assertEqual(obj.name, "Jita IV - Moon 4 - Caldari Navy Assembly Plant")
        self.assertEqual(obj.eve_solar_system, self.jita)
        self.assertEqual(obj.eve_type, self.jita_trade_hub)
        self.assertEqual(obj.owner, self.corporation_2002)

    def test_propagates_http_error_on_station_create(self, mock_esi):
        mock_esi.client = esi_client_stub

        with self.assertRaises(HTTPNotFound):
            Location.objects.update_or_create_esi(id=63999999, token=self.token)

    # Solar System

    def test_can_create_solar_system(self, mock_esi):
        mock_esi.client = esi_client_stub

        obj, created = Location.objects.update_or_create_esi(
            id=30002537, token=self.token
        )
        self.assertTrue(created)
        self.assertEqual(obj.id, 30002537)
        self.assertEqual(obj.name, "Amamake")
        self.assertEqual(obj.eve_solar_system, self.amamake)
        self.assertEqual(obj.eve_type, EveType.objects.get(id=5))
        self.assertIsNone(obj.owner)

    # Asset Safety

    def test_can_create_asset_safety(self, mock_esi):
        # given
        mock_esi.client = esi_client_stub
        # when
        obj, created = Location.objects.update_or_create_esi(id=2004, token=self.token)
        # then
        self.assertTrue(created)
        self.assertEqual(obj.id, 2004)
        self.assertEqual(obj.name, "ASSET SAFETY")
        self.assertIsNone(obj.eve_solar_system)
        self.assertIsNone(obj.owner)
        self.assertEqual(obj.eve_type, EveType.objects.get(id=60))


@patch(MANAGERS_PATH + ".esi")
class TestLocationManagerAsync(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()
        load_entities()
        cls.jita = EveSolarSystem.objects.get(id=30000142)
        cls.amamake = EveSolarSystem.objects.get(id=30002537)
        cls.astrahus = EveType.objects.get(id=35832)
        cls.athanor = EveType.objects.get(id=35835)
        cls.jita_trade_hub = EveType.objects.get(id=52678)
        cls.corporation_2001 = EveEntity.objects.get(id=2001)
        cls.corporation_2002 = EveEntity.objects.get(id=2002)
        cls.character = create_memberaudit_character(1001)
        cls.token = (
            cls.character.eve_character.character_ownership.user.token_set.first()
        )

    def setUp(self) -> None:
        cache.clear()

    @override_settings(
        CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True
    )
    @patch(MANAGERS_PATH + ".fetch_esi_status")
    def test_can_create_structure_async(self, mock_fetch_esi_status, mock_esi):
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        mock_esi.client = esi_client_stub

        obj, created = Location.objects.update_or_create_esi_async(
            id=1000000000001, token=self.token
        )
        self.assertTrue(created)
        self.assertEqual(obj.id, 1000000000001)
        self.assertIsNone(obj.eve_solar_system)
        self.assertIsNone(obj.eve_type)

        obj.refresh_from_db()
        self.assertEqual(obj.name, "Amamake - Test Structure Alpha")
        self.assertEqual(obj.eve_solar_system, self.amamake)
        self.assertEqual(obj.eve_type, self.astrahus)
        self.assertEqual(obj.owner, self.corporation_2001)

        self.assertTrue(mock_fetch_esi_status.called)  # proofs task was called


class TestSkillSetManager(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()
        load_entities()
        cls.fitting = create_fitting(name="My fitting")

    def test_should_create_new_skill_set_from_fitting(self):
        # when
        skill_set, created = SkillSet.objects.update_or_create_from_fitting(
            fitting=self.fitting
        )
        # then
        self.assertTrue(created)
        self.assertEqual(skill_set.name, "My fitting")
        self.assertEqual(skill_set.ship_type.name, "Tristan")
        skills_str = {skill.required_skill_str for skill in skill_set.skills.all()}
        self.assertSetEqual(
            skills_str,
            {
                "Small Autocannon Specialization I",
                "Gunnery II",
                "Weapon Upgrades IV",
                "Light Drone Operation V",
                "Small Projectile Turret V",
                "Gallente Frigate I",
                "Propulsion Jamming II",
                "Drones V",
                "Amarr Drone Specialization I",
            },
        )

    def test_should_create_new_skill_set_from_fitting_and_assign_to_group(self):
        # given
        skill_set_group = create_skill_set_group()
        # when
        skill_set, created = SkillSet.objects.update_or_create_from_fitting(
            fitting=self.fitting, skill_set_group=skill_set_group
        )
        # then
        self.assertTrue(created)
        self.assertIn(skill_set, skill_set_group.skill_sets.all())

    def test_should_create_new_skill_set_from_skill_plan(self):
        # given
        skills = [
            create_skill(
                eve_type=EveType.objects.get(name="Small Autocannon Specialization"),
                level=1,
            ),
            create_skill(
                eve_type=EveType.objects.get(name="Light Drone Operation"),
                level=5,
            ),
        ]
        skill_plan = create_skill_plan(name="My skill plan", skills=skills)
        # when
        skill_set, created = SkillSet.objects.update_or_create_from_skill_plan(
            skill_plan=skill_plan
        )
        # then
        self.assertTrue(created)
        self.assertEqual(skill_set.name, "My skill plan")
        skills_str = {skill.required_skill_str for skill in skill_set.skills.all()}
        self.assertSetEqual(
            skills_str,
            {"Small Autocannon Specialization I", "Light Drone Operation V"},
        )

    def test_should_create_new_skill_set_from_skill_plan_and_assign_to_group(self):
        # given
        # given
        skills = [
            create_skill(
                eve_type=EveType.objects.get(name="Small Autocannon Specialization"),
                level=1,
            ),
            create_skill(
                eve_type=EveType.objects.get(name="Light Drone Operation"),
                level=5,
            ),
        ]
        skill_plan = create_skill_plan(name="My skill plan", skills=skills)
        skill_set_group = create_skill_set_group()
        # when
        skill_set, created = SkillSet.objects.update_or_create_from_skill_plan(
            skill_plan=skill_plan, skill_set_group=skill_set_group
        )
        # then
        self.assertTrue(created)
        self.assertIn(skill_set, skill_set_group.skill_sets.all())
