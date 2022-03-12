from allianceauth.eveonline.models import EveCorporationInfo
from allianceauth.notifications.models import Notification
from app_utils.testing import (
    NoSocketsTestCase,
    create_authgroup,
    create_state,
    create_user_from_evecharacter,
)

from ..models import ComplianceGroupDesignation, SkillSet
from .testdata.factories import (
    create_compliance_group,
    create_fitting,
    create_skill_set_group,
)
from .testdata.load_entities import load_entities
from .testdata.load_eveuniverse import load_eveuniverse
from .utils import add_auth_character_to_user, add_memberaudit_character_to_user

MANAGER_PATH = "memberaudit.managers.general"


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


class TestSkillSetManager(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()
        load_entities()
        cls.fitting = create_fitting(name="My fitting")

    def test_should_create_new_skill_set(self):
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

    def test_should_create_new_skill_set_and_assign_to_group(self):
        # given
        skill_set_group = create_skill_set_group()
        # when
        skill_set, created = SkillSet.objects.update_or_create_from_fitting(
            fitting=self.fitting, skill_set_group=skill_set_group
        )
        # then
        self.assertTrue(created)
        self.assertIn(skill_set, skill_set_group.skill_sets.all())
