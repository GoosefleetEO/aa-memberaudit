from unittest.mock import Mock, patch

from django.contrib.auth.models import Group, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from eveuniverse.models import EveEntity, EveType

from allianceauth.authentication.models import State
from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils
from app_utils.testing import (
    create_user_from_evecharacter,
    generate_invalid_pk,
    json_response_to_dict,
    json_response_to_python,
    multi_assert_in,
    multi_assert_not_in,
)

from ..models import Character, CharacterMail, CharacterSkill, SkillSet, SkillSetGroup
from ..views import (
    add_character,
    admin_create_skillset_from_fitting,
    character_mail,
    character_mail_headers_by_label_data,
    character_mail_headers_by_list_data,
    corporation_compliance_report_data,
    remove_character,
    share_character,
    skill_sets_report_data,
    unshare_character,
    user_compliance_report_data,
)
from .testdata.factories import (
    create_character_mail,
    create_character_mail_label,
    create_compliance_group,
    create_fitting_text,
    create_mail_entity_from_eve_entity,
    create_mailing_list,
    create_skill_set,
    create_skill_set_group,
    create_skill_set_skill,
)
from .testdata.load_entities import load_entities
from .testdata.load_eveuniverse import load_eveuniverse
from .utils import (
    add_auth_character_to_user,
    add_memberaudit_character_to_user,
    create_memberaudit_character,
    create_user_from_evecharacter_with_access,
)

MODULE_PATH = "memberaudit.views"


class TestMailData(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        load_eveuniverse()
        load_entities()
        cls.character = create_memberaudit_character(1001)
        cls.user = cls.character.character_ownership.user
        cls.corporation_2001 = EveEntity.objects.get(id=2001)
        cls.label_1 = create_character_mail_label(character=cls.character)
        cls.label_2 = create_character_mail_label(character=cls.character)
        sender_1002 = create_mail_entity_from_eve_entity(id=1002)
        recipient_1001 = create_mail_entity_from_eve_entity(id=1001)
        cls.mailing_list_5 = create_mailing_list()
        cls.mail_1 = create_character_mail(
            character=cls.character,
            sender=sender_1002,
            recipients=[recipient_1001, cls.mailing_list_5],
            labels=[cls.label_1],
        )
        cls.mail_2 = create_character_mail(
            character=cls.character, sender=sender_1002, labels=[cls.label_2]
        )
        cls.mail_3 = create_character_mail(
            character=cls.character, sender=cls.mailing_list_5
        )
        cls.mail_4 = create_character_mail(
            character=cls.character, sender=sender_1002, recipients=[cls.mailing_list_5]
        )

    def test_mail_by_Label(self):
        """returns list of mails for given label only"""
        # given
        request = self.factory.get(
            reverse(
                "memberaudit:character_mail_headers_by_label_data",
                args=[self.character.pk, self.label_1.label_id],
            )
        )
        request.user = self.user
        # when
        response = character_mail_headers_by_label_data(
            request, self.character.pk, self.label_1.label_id
        )
        # then
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertSetEqual({x["mail_id"] for x in data}, {self.mail_1.mail_id})
        row = data[0]
        self.assertEqual(row["mail_id"], self.mail_1.mail_id)
        self.assertEqual(row["from"], "Clark Kent")
        self.assertIn("Bruce Wayne", row["to"])
        self.assertIn(self.mailing_list_5.name, row["to"])

    def test_all_mails(self):
        """can return all mails"""
        # given
        request = self.factory.get(
            reverse(
                "memberaudit:character_mail_headers_by_label_data",
                args=[self.character.pk, 0],
            )
        )
        request.user = self.user
        # when
        response = character_mail_headers_by_label_data(request, self.character.pk, 0)
        # then
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertSetEqual(
            {x["mail_id"] for x in data},
            {
                self.mail_1.mail_id,
                self.mail_2.mail_id,
                self.mail_3.mail_id,
                self.mail_4.mail_id,
            },
        )

    def test_mail_to_mailinglist(self):
        """can return mail sent to mailing list"""
        # given
        request = self.factory.get(
            reverse(
                "memberaudit:character_mail_headers_by_list_data",
                args=[self.character.pk, self.mailing_list_5.id],
            )
        )
        request.user = self.user
        # when
        response = character_mail_headers_by_list_data(
            request, self.character.pk, self.mailing_list_5.id
        )
        # then
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertSetEqual(
            {x["mail_id"] for x in data}, {self.mail_1.mail_id, self.mail_4.mail_id}
        )
        row = data[0]
        self.assertIn("Bruce Wayne", row["to"])
        self.assertIn("Mailing List", row["to"])

    def test_character_mail_data_normal(self):
        # given
        request = self.factory.get(
            reverse(
                "memberaudit:character_mail", args=[self.character.pk, self.mail_1.pk]
            )
        )
        request.user = self.user
        # when
        response = character_mail(request, self.character.pk, self.mail_1.pk)
        # then
        self.assertEqual(response.status_code, 200)

    def test_character_mail_data_normal_special_chars(self):
        # given
        mail = create_character_mail(character=self.character, body="{}abc")
        request = self.factory.get(
            reverse("memberaudit:character_mail", args=[self.character.pk, mail.pk])
        )
        request.user = self.user
        # when
        response = character_mail(request, self.character.pk, mail.pk)
        # then
        self.assertEqual(response.status_code, 200)

    def test_character_mail_data_error(self):
        invalid_mail_pk = generate_invalid_pk(CharacterMail)
        request = self.factory.get(
            reverse(
                "memberaudit:character_mail",
                args=[self.character.pk, invalid_mail_pk],
            )
        )
        request.user = self.user
        response = character_mail(request, self.character.pk, invalid_mail_pk)
        self.assertEqual(response.status_code, 404)


@patch(MODULE_PATH + ".messages")
@patch(MODULE_PATH + ".tasks")
@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class TestAddCharacter(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        load_entities()
        create_compliance_group()

    def _add_character(self, user, token):
        request = self.factory.get(reverse("memberaudit:add_character"))
        request.user = user
        request.token = token
        middleware = SessionMiddleware(Mock())
        middleware.process_request(request)
        orig_view = add_character.__wrapped__.__wrapped__.__wrapped__
        return orig_view(request, token)

    def test_should_add_character(self, mock_tasks, mock_messages):
        # given
        user, _ = create_user_from_evecharacter(
            1001,
            permissions=["memberaudit.basic_access"],
            scopes=Character.get_esi_scopes(),
        )
        token = user.token_set.get(character_id=1001)
        # when
        response = self._add_character(user, token)
        # then
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("memberaudit:launcher"))
        self.assertTrue(mock_tasks.update_character.delay.called)
        self.assertTrue(mock_tasks.update_compliancegroups_for_user.delay.called)
        self.assertTrue(mock_messages.success.called)
        self.assertTrue(
            Character.objects.filter(
                character_ownership__character__character_id=1001
            ).exists()
        )

    def test_should_not_add_character(self, mock_tasks, mock_messages):
        # given
        user, _ = create_user_from_evecharacter(
            1001,
            permissions=["memberaudit.basic_access"],
            scopes=Character.get_esi_scopes(),
        )
        user_2, _ = create_user_from_evecharacter(1002)
        token = user_2.token_set.get(character_id=1002)
        # when
        response = self._add_character(user, token)
        # then
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("memberaudit:launcher"))
        self.assertFalse(mock_tasks.update_character.delay.called)
        self.assertFalse(mock_tasks.update_compliancegroups_for_user.delay.called)
        self.assertTrue(mock_messages.error.called)
        self.assertFalse(
            Character.objects.filter(
                character_ownership__character__character_id=1002
            ).exists()
        )


@patch(MODULE_PATH + ".messages")
@patch(MODULE_PATH + ".tasks")
@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class TestRemoveCharacter(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        load_entities()
        create_compliance_group()

    def _remove_character(self, user, character_pk):
        request = self.factory.get(
            reverse("memberaudit:remove_character", args=[character_pk])
        )
        request.user = user
        return remove_character(request, character_pk)

    def test_should_remove_character(self, mock_tasks, mock_messages):
        # given
        character = create_memberaudit_character(1001)
        user = character.character_ownership.user
        # when
        response = self._remove_character(user, character.pk)
        # then
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("memberaudit:launcher"))
        self.assertFalse(Character.objects.filter(pk=character.pk).exists())
        self.assertTrue(mock_tasks.update_compliancegroups_for_user.delay.called)
        self.assertTrue(mock_messages.success.called)

    def test_should_not_remove_character_from_another_user(
        self, mock_tasks, mock_messages
    ):
        # given
        character_1001 = create_memberaudit_character(1001)
        user_1002, _ = create_user_from_evecharacter_with_access(1002)
        # when
        response = self._remove_character(user_1002, character_1001.pk)
        # then
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Character.objects.filter(pk=character_1001.pk).exists())
        self.assertFalse(mock_tasks.update_compliancegroups_for_user.delay.called)
        self.assertFalse(mock_messages.success.called)

    def test_should_respond_with_not_found_for_invalid_characters(
        self, mock_tasks, mock_messages
    ):
        # given
        character = create_memberaudit_character(1001)
        user = character.character_ownership.user
        invalid_character_pk = generate_invalid_pk(Character)
        # when
        response = self._remove_character(user, invalid_character_pk)
        # then
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Character.objects.filter(pk=character.pk).exists())
        self.assertFalse(mock_tasks.update_compliancegroups_for_user.delay.called)
        self.assertFalse(mock_messages.success.called)


class TestShareCharacter(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        load_entities()

    def setUp(self) -> None:
        self.character_1001 = create_memberaudit_character(1001)
        self.user_1001 = self.character_1001.character_ownership.user
        self.user_1001 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.share_characters", self.user_1001
        )

        self.character_1002 = create_memberaudit_character(1002)
        self.user_1002 = self.character_1002.character_ownership.user
        self.user_1002 = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.share_characters", self.user_1002
        )

    def test_normal(self):
        request = self.factory.get(
            reverse("memberaudit:share_character", args=[self.character_1001.pk])
        )
        request.user = self.user_1001
        response = share_character(request, self.character_1001.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("memberaudit:launcher"))
        self.assertTrue(Character.objects.get(pk=self.character_1001.pk).is_shared)

    def test_no_permission_1(self):
        """
        when user does not have any permissions
        then redirect to login
        """
        user = AuthUtils.create_user("John Doe")
        request = self.factory.get(
            reverse("memberaudit:share_character", args=[self.character_1001.pk])
        )
        request.user = user
        response = share_character(request, self.character_1001.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_no_permission_2(self):
        """
        when user does has basic_access only
        then redirect to login
        """
        user = AuthUtils.create_user("John Doe")
        user = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.basic_access", user
        )
        request = self.factory.get(
            reverse("memberaudit:share_character", args=[self.character_1001.pk])
        )
        request.user = user
        response = share_character(request, self.character_1001.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_no_permission_3(self):
        request = self.factory.get(
            reverse("memberaudit:share_character", args=[self.character_1001.pk])
        )
        request.user = self.user_1002
        response = share_character(request, self.character_1001.pk)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Character.objects.get(pk=self.character_1001.pk).is_shared)

    def test_not_found(self):
        invalid_character_pk = generate_invalid_pk(Character)
        request = self.factory.get(
            reverse("memberaudit:share_character", args=[invalid_character_pk])
        )
        request.user = self.user_1001
        response = share_character(request, invalid_character_pk)
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Character.objects.get(pk=self.character_1001.pk).is_shared)


class TestUnshareCharacter(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        load_entities()

    def setUp(self) -> None:
        self.character_1001 = create_memberaudit_character(1001)
        self.character_1001.is_shared = True
        self.character_1001.save()
        self.user_1001 = self.character_1001.character_ownership.user

        self.character_1002 = create_memberaudit_character(1002)
        self.user_1002 = self.character_1002.character_ownership.user

    def test_normal(self):
        request = self.factory.get(
            reverse("memberaudit:unshare_character", args=[self.character_1001.pk])
        )
        request.user = self.user_1001
        response = unshare_character(request, self.character_1001.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("memberaudit:launcher"))
        self.assertFalse(Character.objects.get(pk=self.character_1001.pk).is_shared)

    def test_no_permission(self):
        request = self.factory.get(
            reverse("memberaudit:unshare_character", args=[self.character_1001.pk])
        )
        request.user = self.user_1002
        response = unshare_character(request, self.character_1001.pk)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Character.objects.get(pk=self.character_1001.pk).is_shared)

    def test_not_found(self):
        invalid_character_pk = generate_invalid_pk(Character)
        request = self.factory.get(
            reverse("memberaudit:unshare_character", args=[invalid_character_pk])
        )
        request.user = self.user_1001
        response = unshare_character(request, invalid_character_pk)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Character.objects.get(pk=self.character_1001.pk).is_shared)


class TestUserComplianceReportTestData(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        load_eveuniverse()
        load_entities()
        # given
        state = AuthUtils.get_member_state()
        state_alliance = EveAllianceInfo.objects.get(alliance_id=3001)
        state.member_alliances.add(state_alliance)
        state_corporation = EveCorporationInfo.objects.get(corporation_id=2103)
        state.member_corporations.add(state_corporation)
        cls.character_1001 = create_memberaudit_character(1001)
        cls.character_1002 = create_memberaudit_character(1002)
        cls.character_1003 = create_memberaudit_character(1003)
        cls.character_1101 = create_memberaudit_character(1101)
        cls.user_1103 = create_user_from_evecharacter_with_access(1103)[0]
        cls.user = cls.character_1001.character_ownership.user
        cls.user = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.reports_access", cls.user
        )
        AuthUtils.create_user("John Doe")  # this user should not show up in view

    def _execute_request(self) -> dict:
        request = self.factory.get(reverse("memberaudit:user_compliance_report_data"))
        request.user = self.user
        response = user_compliance_report_data(request)
        self.assertEqual(response.status_code, 200)
        return json_response_to_dict(response)

    def test_should_show_own_user_only(self):
        # when
        result = self._execute_request()
        # then
        self.assertSetEqual(set(result.keys()), {self.user.pk})

    def test_should_return_non_guests_only(self):
        # given
        self.user = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_everything", self.user
        )
        # when
        result = self._execute_request()
        # then
        self.assertSetEqual(
            set(result.keys()),
            {
                self.character_1001.character_ownership.user.pk,
                self.character_1002.character_ownership.user.pk,
                self.character_1003.character_ownership.user.pk,
                self.user_1103.pk,
            },
        )

    def test_should_include_character_links(self):
        # given
        self.user = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_everything", self.user
        )
        self.user = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.characters_access", self.user
        )
        # when
        result = self._execute_request()
        # then
        self.assertSetEqual(
            set(result.keys()),
            {
                self.character_1001.character_ownership.user.pk,
                self.character_1002.character_ownership.user.pk,
                self.character_1003.character_ownership.user.pk,
                self.user_1103.pk,
            },
        )

    def test_char_counts(self):
        # given
        self.user = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_everything", self.user
        )
        user = self.character_1002.character_ownership.user
        add_auth_character_to_user(user, 1103)
        group, _ = Group.objects.get_or_create(name="Test Group")
        AuthUtils.add_permissions_to_groups(
            [AuthUtils.get_permission_by_name("memberaudit.basic_access")], [group]
        )
        user.groups.add(group)
        # when
        result = self._execute_request()
        # then
        result_1002 = result[user.pk]
        self.assertEqual(result_1002["total_chars"], 2)
        self.assertEqual(result_1002["unregistered_chars"], 1)


class TestCorporationComplianceReportTestData(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        load_eveuniverse()
        load_entities()
        # given
        member_state = State.objects.get(name="Member")
        member_state.member_alliances.add(EveAllianceInfo.objects.get(alliance_id=3001))
        member_state.member_corporations.add(
            EveCorporationInfo.objects.get(corporation_id=2110)
        )
        cls.character_1001 = create_memberaudit_character(1001)
        add_auth_character_to_user(cls.character_1001.character_ownership.user, 1107)
        cls.character_1002 = create_memberaudit_character(1002)
        add_memberaudit_character_to_user(
            cls.character_1002.character_ownership.user, 1104
        )
        add_auth_character_to_user(cls.character_1002.character_ownership.user, 1105)
        add_auth_character_to_user(cls.character_1002.character_ownership.user, 1106)
        cls.character_1003 = create_memberaudit_character(1003)
        add_memberaudit_character_to_user(
            cls.character_1003.character_ownership.user, 1101
        )
        add_memberaudit_character_to_user(
            cls.character_1003.character_ownership.user, 1102
        )
        cls.user_1103 = create_user_from_evecharacter_with_access(1103)[0]
        cls.user = cls.character_1001.character_ownership.user
        cls.user = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.reports_access", cls.user
        )
        cls.character_1110 = create_memberaudit_character(1110)

    def _corporation_compliance_report_data(self, user) -> dict:
        request = self.factory.get(
            reverse("memberaudit:corporation_compliance_report_data")
        )
        request.user = user
        response = corporation_compliance_report_data(request)
        self.assertEqual(response.status_code, 200)
        return json_response_to_dict(response)

    def test_should_return_full_list(self):
        # given
        self.user = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_everything", self.user
        )
        # when
        result = self._corporation_compliance_report_data(self.user)
        # then
        self.assertSetEqual(set(result.keys()), {2001, 2002, 2110})
        row = result[2001]
        self.assertEqual(row["corporation_name"], "Wayne Technologies")
        self.assertEqual(row["mains_count"], 2)
        self.assertEqual(row["characters_count"], 6)
        self.assertEqual(row["unregistered_count"], 3)
        self.assertEqual(row["compliance_percent"], 50)
        self.assertFalse(row["is_compliant"])
        self.assertFalse(row["is_partly_compliant"])
        row = result[2002]
        self.assertEqual(row["corporation_name"], "Wayne Food")
        self.assertEqual(row["mains_count"], 1)
        self.assertEqual(row["characters_count"], 3)
        self.assertEqual(row["unregistered_count"], 0)
        self.assertEqual(row["compliance_percent"], 100)
        self.assertTrue(row["is_compliant"])
        self.assertTrue(row["is_partly_compliant"])

    def test_should_return_my_corporation_only(self):
        # given
        self.user = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_corporation", self.user
        )
        # when
        result = self._corporation_compliance_report_data(self.user)
        # then
        self.assertSetEqual(set(result.keys()), {2001})


class TestSkillSetReportData(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        load_eveuniverse()
        load_entities()
        state = AuthUtils.get_member_state()
        state.member_alliances.add(EveAllianceInfo.objects.get(alliance_id=3001))

        # user 1 is manager requesting the report
        cls.character_1001 = create_memberaudit_character(1001)
        cls.user = cls.character_1001.character_ownership.user
        cls.user = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.reports_access", cls.user
        )
        cls.user = AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_everything", cls.user
        )

        # user 2 is normal user and has two characters
        cls.character_1002 = create_memberaudit_character(1002)
        cls.character_1101 = add_memberaudit_character_to_user(
            cls.character_1002.character_ownership.user, 1101
        )
        # cls.character_1003 = create_memberaudit_character(1003)

        cls.skill_type_1 = EveType.objects.get(id=24311)
        cls.skill_type_2 = EveType.objects.get(id=24312)

        AuthUtils.create_user("John Doe")  # this user should not show up in view
        cls.character_1103 = create_memberaudit_character(1103)

    def test_normal(self):
        def make_data_id(doctrine: SkillSetGroup, character: Character) -> str:
            doctrine_pk = doctrine.pk if doctrine else 0
            return f"{doctrine_pk}_{character.pk}"

        # define doctrines
        ship_1 = create_skill_set(name="Ship 1")
        create_skill_set_skill(
            skill_set=ship_1, eve_type=self.skill_type_1, required_level=3
        )

        ship_2 = create_skill_set(name="Ship 2")
        create_skill_set_skill(
            skill_set=ship_2, eve_type=self.skill_type_1, required_level=5
        )
        create_skill_set_skill(
            skill_set=ship_2, eve_type=self.skill_type_2, required_level=3
        )

        ship_3 = create_skill_set(name="Ship 3")
        create_skill_set_skill(
            skill_set=ship_3, eve_type=self.skill_type_1, required_level=1
        )

        doctrine_1 = create_skill_set_group(name="Alpha")
        doctrine_1.skill_sets.add(ship_1)
        doctrine_1.skill_sets.add(ship_2)

        doctrine_2 = create_skill_set_group(name="Bravo", is_doctrine=True)
        doctrine_2.skill_sets.add(ship_1)

        # character 1002
        CharacterSkill.objects.create(
            character=self.character_1002,
            eve_type=self.skill_type_1,
            active_skill_level=5,
            skillpoints_in_skill=10,
            trained_skill_level=5,
        )
        CharacterSkill.objects.create(
            character=self.character_1002,
            eve_type=self.skill_type_2,
            active_skill_level=2,
            skillpoints_in_skill=10,
            trained_skill_level=2,
        )

        # character 1101
        CharacterSkill.objects.create(
            character=self.character_1101,
            eve_type=self.skill_type_1,
            active_skill_level=5,
            skillpoints_in_skill=10,
            trained_skill_level=5,
        )
        CharacterSkill.objects.create(
            character=self.character_1101,
            eve_type=self.skill_type_2,
            active_skill_level=5,
            skillpoints_in_skill=10,
            trained_skill_level=5,
        )

        self.character_1001.update_skill_sets()
        self.character_1002.update_skill_sets()
        self.character_1101.update_skill_sets()
        self.character_1103.update_skill_sets()

        request = self.factory.get(reverse("memberaudit:skill_sets_report_data"))
        request.user = self.user
        response = skill_sets_report_data(request)

        self.assertEqual(response.status_code, 200)
        data = json_response_to_dict(response)
        self.assertEqual(len(data), 9)

        mains = {x["main"] for x in data.values()}
        self.assertSetEqual(mains, {"Bruce Wayne", "Clark Kent"})

        row = data[make_data_id(doctrine_1, self.character_1001)]
        self.assertEqual(row["group"], "Alpha")
        self.assertEqual(row["character"], "Bruce Wayne")
        self.assertEqual(row["main"], "Bruce Wayne")
        self.assertTrue(multi_assert_not_in(["Ship 1", "Ship 2"], row["has_required"]))

        row = data[make_data_id(doctrine_1, self.character_1002)]
        self.assertEqual(row["group"], "Alpha")
        self.assertEqual(row["character"], "Clark Kent")
        self.assertEqual(row["main"], "Clark Kent")

        self.assertTrue(multi_assert_in(["Ship 1"], row["has_required"]))
        self.assertTrue(multi_assert_not_in(["Ship 2", "Ship 3"], row["has_required"]))

        row = data[make_data_id(doctrine_1, self.character_1101)]
        self.assertEqual(row["group"], "Alpha")
        self.assertEqual(row["character"], "Lex Luther")
        self.assertEqual(row["main"], "Clark Kent")
        self.assertTrue(multi_assert_in(["Ship 1", "Ship 2"], row["has_required"]))

        row = data[make_data_id(doctrine_2, self.character_1101)]
        self.assertEqual(row["group"], "Doctrine: Bravo")
        self.assertEqual(row["character"], "Lex Luther")
        self.assertEqual(row["main"], "Clark Kent")
        self.assertTrue(multi_assert_in(["Ship 1"], row["has_required"]))
        self.assertTrue(multi_assert_not_in(["Ship 2"], row["has_required"]))

        row = data[make_data_id(None, self.character_1101)]
        self.assertEqual(row["group"], "[Ungrouped]")
        self.assertEqual(row["character"], "Lex Luther")
        self.assertEqual(row["main"], "Clark Kent")
        self.assertTrue(multi_assert_in(["Ship 3"], row["has_required"]))

    # def test_can_handle_user_without_main(self):
    #     character = create_memberaudit_character(1102)
    #     user = character.character_ownership.user
    #     user.profile.main_character = None
    #     user.profile.save()

    #     ship_1 = create_skill_set(name="Ship 1")
    #     create_skill_set_skill(
    #         skill_set=ship_1, eve_type=self.skill_type_1, required_level=3
    #     )
    #     doctrine_1 = create_skill_set_group(name="Alpha")
    #     doctrine_1.skill_sets.add(ship_1)

    #     request = self.factory.get(reverse("memberaudit:skill_sets_report_data"))
    #     request.user = self.user
    #     response = skill_sets_report_data(request)
    #     data = json_response_to_dict(response)
    #     self.assertEqual(len(data), 4)


@patch(MODULE_PATH + ".messages")
@patch(MODULE_PATH + ".tasks")
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
