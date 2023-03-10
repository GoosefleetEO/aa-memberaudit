from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from esi.errors import TokenError
from esi.models import Token

from allianceauth.tests.auth_utils import AuthUtils
from app_utils.testing import NoSocketsTestCase, generate_invalid_pk

from ..decorators import fetch_character_if_allowed, fetch_token_for_character
from ..models import Character
from .testdata.load_entities import load_entities
from .utils import create_memberaudit_character, scope_names_set

DUMMY_URL = "http://www.example.com"


class TestFetchOwnerIfAllowed(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        load_entities()

    def test_passthrough_when_fetch_owner_if_allowed(self):
        @fetch_character_if_allowed()
        def dummy(request, character_pk, character):
            self.assertEqual(character, my_character)
            self.assertIn("eve_character", character._state.fields_cache)
            return HttpResponse("ok")

        # given
        my_character = create_memberaudit_character(1001)
        user = my_character.eve_character.character_ownership.user
        request = self.factory.get(DUMMY_URL)
        request.user = user
        # when
        response = dummy(request, my_character.pk)
        # then
        self.assertEqual(response.status_code, 200)

    def test_returns_404_when_owner_not_found(self):
        @fetch_character_if_allowed()
        def dummy(request, character_pk, character):
            self.assertTrue(False)

        # given
        my_character = create_memberaudit_character(1001)
        user = my_character.eve_character.character_ownership.user
        request = self.factory.get(DUMMY_URL)
        request.user = user
        # when
        response = dummy(request, generate_invalid_pk(Character))
        # then
        self.assertEqual(response.status_code, 404)

    def test_returns_403_when_user_has_not_access(self):
        @fetch_character_if_allowed()
        def dummy(request, character_pk, character):
            self.assertTrue(False)

        # given
        my_character = create_memberaudit_character(1001)
        user_2 = AuthUtils.create_user("Lex Luthor")
        request = self.factory.get(DUMMY_URL)
        request.user = user_2
        # when
        response = dummy(request, my_character.pk)
        # then
        self.assertEqual(response.status_code, 403)

    """
    TODO: create test case with CharacterDetails
    def test_can_specify_list_for_select_related(self):
        @fetch_character_if_allowed("skills")
        def dummy(request, character_pk, character):
            self.assertEqual(character, self.character)
            self.assertIn("skills", character._state.fields_cache)
            return HttpResponse("ok")

        OwnerSkills.objects.create(character=self.character, total_sp=10000000)
        request = self.factory.get(DUMMY_URL)
        request.user = self.user
        dummy(request, self.character.pk)
    """


class TestFetchToken(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_entities()

    def setUp(self) -> None:
        self.character = create_memberaudit_character(1001)

    def test_defaults(self):
        @fetch_token_for_character()
        def dummy(character, token):
            self.assertIsInstance(token, Token)
            self.assertSetEqual(scope_names_set(token), set(Character.get_esi_scopes()))

        dummy(self.character)

    def test_specified_scope(self):
        @fetch_token_for_character("esi-mail.read_mail.v1")
        def dummy(character, token):
            self.assertIsInstance(token, Token)
            self.assertIn("esi-mail.read_mail.v1", scope_names_set(token))

        dummy(self.character)

    def test_exceptions_if_not_found(self):
        @fetch_token_for_character("invalid_scope")
        def dummy(character, token):
            pass

        with self.assertRaises(TokenError):
            dummy(self.character)
