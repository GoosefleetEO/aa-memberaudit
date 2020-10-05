import json
from unittest.mock import patch, Mock

from bravado.exception import HTTPNotFound

from django.http import JsonResponse
from django.test import TestCase, RequestFactory
from django.utils.timezone import now
from django.urls import reverse

from eveuniverse.models import EveSolarSystem, EveType, EveEntity

from allianceauth.eveonline.models import EveAllianceInfo
from allianceauth.tests.auth_utils import AuthUtils

from .testdata.load_eveuniverse import load_eveuniverse
from .testdata.load_entities import load_entities
from .testdata.load_locations import load_locations

from . import create_memberaudit_character
from ..models import (
    Character,
    CharacterJumpClone,
    CharacterJumpCloneImplant,
    CharacterMail,
    CharacterMailRecipient,
    CharacterMailingList,
    CharacterSkill,
    CharacterWalletJournalEntry,
    Location,
)
from .utils import reload_user
from ..utils import generate_invalid_pk
from ..views import (
    launcher,
    character_viewer,
    character_location_data,
    character_jump_clones_data,
    character_mail_headers_data,
    character_mail_data,
    character_skills_data,
    character_wallet_journal_data,
    character_finder_data,
    compliance_report_data,
    remove_character,
    share_character,
    unshare_character,
)

MODULE_PATH = "memberaudit.views"


def json_response_to_python(response: JsonResponse) -> object:
    return json.loads(response.content.decode("utf-8"))


class TestViews(TestCase):
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
        cls.jita_station = Location.objects.get(id=60003760)

    def test_can_open_launcher_view(self):
        request = self.factory.get(reverse("memberaudit:launcher"))
        request.user = self.user
        response = launcher(request)
        self.assertEqual(response.status_code, 200)

    def test_can_open_character_main_view(self):
        request = self.factory.get(
            reverse("memberaudit:character_viewer", args=[self.character.pk])
        )
        request.user = self.user
        response = character_viewer(request, self.character.pk)
        self.assertEqual(response.status_code, 200)

    def test_character_jump_clones_data(self):
        jump_clone = CharacterJumpClone.objects.create(
            character=self.character, location=self.jita_station, jump_clone_id=1
        )
        CharacterJumpCloneImplant.objects.create(
            jump_clone=jump_clone, eve_type=EveType.objects.get(id=19540)
        )
        CharacterJumpCloneImplant.objects.create(
            jump_clone=jump_clone, eve_type=EveType.objects.get(id=19551)
        )

        location_2 = Location.objects.create(id=123457890)
        jump_clone = CharacterJumpClone.objects.create(
            character=self.character, location=location_2, jump_clone_id=2
        )
        request = self.factory.get(
            reverse("memberaudit:character_jump_clones_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_jump_clones_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 2)

        row = data[0]
        self.assertEqual(row["region"], "The Forge")
        self.assertIn("Jita", row["solar_system"])
        self.assertEqual(
            row["location"], "Jita IV - Moon 4 - Caldari Navy Assembly Plant"
        )
        self.assertEqual(
            row["implants"], "High-grade Snake Alpha<br>High-grade Snake Beta"
        )

        row = data[1]
        self.assertEqual(row["region"], "-")
        self.assertEqual(row["solar_system"], "-")
        self.assertEqual(row["location"], "Unknown location #123457890")
        self.assertEqual(row["implants"], "(none)")

    def test_character_skills_data(self):
        CharacterSkill.objects.create(
            character=self.character,
            eve_type=EveType.objects.get(id=24311),
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
        self.assertEqual(row["amount"], "1000000.00")
        self.assertEqual(row["balance"], "10000000.00")

    def test_character_mail_headers_data(self):
        mailing_list = CharacterMailingList.objects.create(
            character=self.character, list_id=5, name="Mailing List"
        )
        mail = CharacterMail.objects.create(
            character=self.character,
            mail_id=99,
            from_entity=EveEntity.objects.get(id=1002),
            subject="Dummy",
            body="This is the body",
            timestamp=now(),
        )
        CharacterMailRecipient.objects.create(
            mail=mail, eve_entity=EveEntity.objects.get(id=1001)
        )
        CharacterMailRecipient.objects.create(mail=mail, mailing_list=mailing_list)
        request = self.factory.get(
            reverse("memberaudit:character_mail_headers_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_mail_headers_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(row["mail_id"], 99)
        self.assertEqual(row["from"], "Clark Kent")
        self.assertEqual(row["to"], "Bruce Wayne, Mailing List")

    def test_character_mail_data(self):
        mailing_list = CharacterMailingList.objects.create(
            character=self.character, list_id=5, name="Mailing List"
        )
        mail = CharacterMail.objects.create(
            character=self.character,
            mail_id=99,
            from_entity=EveEntity.objects.get(id=1002),
            subject="Dummy",
            body="This is the body",
            timestamp=now(),
        )
        CharacterMailRecipient.objects.create(
            mail=mail, eve_entity=EveEntity.objects.get(id=1001)
        )
        CharacterMailRecipient.objects.create(mail=mail, mailing_list=mailing_list)
        request = self.factory.get(
            reverse(
                "memberaudit:character_mail_data", args=[self.character.pk, mail.pk]
            )
        )
        request.user = self.user
        response = character_mail_data(request, self.character.pk, mail.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(data["mail_id"], 99)
        self.assertEqual(data["from"], "Clark Kent")
        self.assertEqual(data["to"], "Bruce Wayne, Mailing List")
        self.assertEqual(data["body"], "This is the body")

    def test_character_finder_data(self):
        AuthUtils.add_permission_to_user_by_name("memberaudit.finder_access", self.user)
        self.user = reload_user(self.user)
        request = self.factory.get(reverse("memberaudit:character_finder_data"))
        request.user = self.user
        response = character_finder_data(request)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertSetEqual({x["character_pk"] for x in data}, {self.character.pk})


@patch(MODULE_PATH + ".messages_plus")
class TestRemoveCharacter(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        load_entities()

    def setUp(self) -> None:
        self.character_1001 = create_memberaudit_character(1001)
        self.user_1001 = self.character_1001.character_ownership.user

        self.character_1002 = create_memberaudit_character(1002)
        self.user_1002 = self.character_1002.character_ownership.user

    def test_normal(self, mock_message_plus):
        request = self.factory.get(
            reverse("memberaudit:remove_character", args=[self.character_1001.pk])
        )
        request.user = self.user_1001
        response = remove_character(request, self.character_1001.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("memberaudit:launcher"))
        self.assertFalse(Character.objects.filter(pk=self.character_1001.pk).exists())
        self.assertTrue(mock_message_plus.success.called)

    def test_no_permission(self, mock_message_plus):
        request = self.factory.get(
            reverse("memberaudit:remove_character", args=[self.character_1001.pk])
        )
        request.user = self.user_1002
        response = remove_character(request, self.character_1001.pk)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Character.objects.filter(pk=self.character_1001.pk).exists())
        self.assertFalse(mock_message_plus.success.called)

    def test_not_found(self, mock_message_plus):
        invalid_character_pk = generate_invalid_pk(Character)
        request = self.factory.get(
            reverse("memberaudit:remove_character", args=[invalid_character_pk])
        )
        request.user = self.user_1001
        response = remove_character(request, invalid_character_pk)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Character.objects.filter(pk=self.character_1001.pk).exists())
        self.assertFalse(mock_message_plus.success.called)


class TestShareCharacter(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        load_entities()

    def setUp(self) -> None:
        self.character_1001 = create_memberaudit_character(1001)
        self.user_1001 = self.character_1001.character_ownership.user

        self.character_1002 = create_memberaudit_character(1002)
        self.user_1002 = self.character_1002.character_ownership.user

    def test_normal(self):
        request = self.factory.get(
            reverse("memberaudit:share_character", args=[self.character_1001.pk])
        )
        request.user = self.user_1001
        response = share_character(request, self.character_1001.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("memberaudit:launcher"))
        self.assertTrue(Character.objects.get(pk=self.character_1001.pk).is_shared)

    def test_no_permission(self):
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


class TestComplianceReportData(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        load_eveuniverse()
        load_entities()
        state = AuthUtils.get_member_state()
        state.member_alliances.add(EveAllianceInfo.objects.get(alliance_id=3001))

        cls.character_1001 = create_memberaudit_character(1001)
        cls.character_1002 = create_memberaudit_character(1002)
        cls.character_1003 = create_memberaudit_character(1003)
        cls.character_1101 = create_memberaudit_character(1101)
        cls.character_1102 = create_memberaudit_character(1102)

        cls.user = cls.character_1001.character_ownership.user
        AuthUtils.add_permission_to_user_by_name("memberaudit.reports_access", cls.user)
        cls.user = reload_user(cls.user)

    @staticmethod
    def user_pks_set(data) -> set:
        return {x["user_pk"] for x in data}

    def _execute_request(self) -> list:
        request = self.factory.get(reverse("memberaudit:compliance_report_data"))
        request.user = self.user
        response = compliance_report_data(request)
        self.assertEqual(response.status_code, 200)
        return json_response_to_python(response)

    def test_no_scope(self):
        result = self._execute_request()
        self.assertSetEqual(self.user_pks_set(result), set())

    def test_corporation_permission(self):
        AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_corporation", self.user
        )
        self.user = reload_user(self.user)
        result = self._execute_request()
        self.assertSetEqual(
            self.user_pks_set(result),
            {
                self.character_1001.character_ownership.user.pk,
                self.character_1002.character_ownership.user.pk,
            },
        )

    def test_alliance_permission(self):
        AuthUtils.add_permission_to_user_by_name(
            "memberaudit.view_same_alliance", self.user
        )
        self.user = reload_user(self.user)
        result = self._execute_request()
        self.assertSetEqual(
            self.user_pks_set(result),
            {
                self.character_1001.character_ownership.user.pk,
                self.character_1002.character_ownership.user.pk,
                self.character_1003.character_ownership.user.pk,
            },
        )


@patch(MODULE_PATH + ".Character.fetch_location")
class TestCharacterLocationData(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        load_eveuniverse()
        load_entities()
        cls.character = create_memberaudit_character(1001)
        cls.user = cls.character.character_ownership.user
        cls.abune = EveSolarSystem.objects.get(id=30004984)

    def test_normal(self, mock_fetch_location):
        mock_fetch_location.return_value = (self.abune, None)

        request = self.factory.get(
            reverse("memberaudit:character_location_data", args=[self.character.pk])
        )
        request.user = self.user
        orig_view = character_location_data.__wrapped__
        response = orig_view(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Abune", response.content.decode("utf8"))

    def test_http_error(self, mock_fetch_location):
        mock_fetch_location.side_effect = HTTPNotFound(
            Mock(**{"response.status_code": 404})
        )

        request = self.factory.get(
            reverse("memberaudit:character_location_data", args=[self.character.pk])
        )
        request.user = self.user
        orig_view = character_location_data.__wrapped__
        response = orig_view(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Network error", response.content.decode("utf8"))

    def test_unexpected_error(self, mock_fetch_location):
        mock_fetch_location.side_effect = RuntimeError

        request = self.factory.get(
            reverse("memberaudit:character_location_data", args=[self.character.pk])
        )
        request.user = self.user
        orig_view = character_location_data.__wrapped__
        response = orig_view(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Unexpected error", response.content.decode("utf8"))