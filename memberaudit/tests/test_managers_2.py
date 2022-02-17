from django.contrib.auth.models import User
from django.test import TestCase

from allianceauth.eveonline.models import EveCorporationInfo
from allianceauth.notifications.models import Notification
from app_utils.testing import (
    create_authgroup,
    create_state,
    create_user_from_evecharacter,
)

from ..models import ComplianceGroupDesignation, General
from .testdata.factories import (
    create_compliance_group,
    create_compliance_group_designation,
)
from .testdata.load_entities import load_entities
from .utils import add_auth_character_to_user, add_memberaudit_character_to_user

MANAGER_PATH = "memberaudit.managers.general"


class TestComplianceGroupDesignation(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_entities()

    def test_should_ensure_new_compliance_groups_are_internal(self):
        # given
        group = create_authgroup(internal=False)
        # when
        create_compliance_group_designation(group)
        # then
        group.refresh_from_db()
        self.assertTrue(group.authgroup.internal)

    def test_should_return_compliant_users_only(self):
        # given
        # compliant user both chars registered
        user_compliant, _ = create_user_from_evecharacter(
            1001, permissions=["memberaudit.basic_access"]
        )
        add_memberaudit_character_to_user(user_compliant, 1001)
        add_memberaudit_character_to_user(user_compliant, 1101)
        # non-compliant user one char not registered
        user_non_compliant_1, _ = create_user_from_evecharacter(
            1002, permissions=["memberaudit.basic_access"]
        )
        add_memberaudit_character_to_user(user_compliant, 1002)
        add_auth_character_to_user(user_non_compliant_1, 1102)
        # non-compliant user with char registered, but missing permission
        user_non_compliant_2, _ = create_user_from_evecharacter(1003)
        add_memberaudit_character_to_user(user_non_compliant_2, 1003)
        # when
        result = General.compliant_users()
        # then
        self.assertQuerysetEqual(result, User.objects.filter(pk=user_compliant.pk))

    def test_should_add_new_group_to_compliant_users(self):
        # given
        compliance_group = create_authgroup(internal=True)
        user_compliant, _ = create_user_from_evecharacter(
            1001, permissions=["memberaudit.basic_access"]
        )
        add_memberaudit_character_to_user(user_compliant, 1001)
        user_non_compliant, _ = create_user_from_evecharacter(
            1002, permissions=["memberaudit.basic_access"]
        )
        # when
        create_compliance_group_designation(group=compliance_group)
        # then
        self.assertIn(compliance_group, user_compliant.groups.all())
        self.assertNotIn(compliance_group, user_non_compliant.groups.all())

    def test_should_add_new_state_group_to_compliant_users_when_state_is_matching(
        self,
    ):
        # given
        member_corporation = EveCorporationInfo.objects.get(corporation_id=2001)
        my_state = create_state(member_corporations=[member_corporation], priority=200)
        compliance_group = create_authgroup(internal=True, states=[my_state])
        user_compliant, _ = create_user_from_evecharacter(
            1001, permissions=["memberaudit.basic_access"]
        )
        add_memberaudit_character_to_user(user_compliant, 1001)
        # when
        create_compliance_group_designation(group=compliance_group)
        # then
        self.assertIn(compliance_group, user_compliant.groups.all())

    def test_should_not_add_new_state_group_to_compliant_user_when_state_not_matching(
        self,
    ):
        # given
        my_state = create_state(priority=200)
        compliance_group = create_authgroup(internal=True, states=[my_state])
        user_compliant, _ = create_user_from_evecharacter(
            1001, permissions=["memberaudit.basic_access"]
        )
        add_memberaudit_character_to_user(user_compliant, 1001)
        # when
        create_compliance_group_designation(group=compliance_group)
        # then
        self.assertNotIn(compliance_group, user_compliant.groups.all())

    def test_should_remove_deleted_compliance_group_from_users(self):
        # given
        compliance_group = create_compliance_group()
        user_compliant, _ = create_user_from_evecharacter(
            1001, permissions=["memberaudit.basic_access"]
        )
        add_memberaudit_character_to_user(user_compliant, 1001)
        user_compliant.groups.add(compliance_group)
        # when
        compliance_group.compliancegroupdesignation.delete()
        # then
        self.assertNotIn(compliance_group, user_compliant.groups.all())

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
