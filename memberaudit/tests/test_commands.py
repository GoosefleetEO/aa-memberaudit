from io import StringIO

from django.core.management import call_command
from django.utils.timezone import now
from eveuniverse.models import EveEntity

from app_utils.testing import NoSocketsTestCase

from ..models import Character, CharacterWalletJournalEntry
from . import (
    add_auth_character_to_user,
    create_memberaudit_character,
    create_user_from_evecharacter,
)
from .testdata.load_entities import load_entities

# from esi.models import Token


# from allianceauth.authentication.models import CharacterOwnership


PACKAGE_PATH = "memberaudit.management.commands"


class TestResetCharacters(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_entities()
        Character.objects.all().delete()

    def test_normal(self):
        """can recreate member audit characters from main and alt of matching tokens"""
        user, co_1001 = create_user_from_evecharacter(1001)
        co_1002 = add_auth_character_to_user(user, 1002)

        out = StringIO()
        call_command("memberaudit_reset_characters", "--noinput", stdout=out)

        self.assertSetEqual(
            set(Character.objects.values_list("character_ownership_id", flat=True)),
            {co_1001.id, co_1002.id},
        )

    def test_orphaned_tokens(self):
        """
        given a matching token exists and the respective auth character
        is now owner by another user
        and no longer has a matching token
        when creating member audit characters
        then no member audit character is created for the switched auth character
        """
        user_1, co_1001 = create_user_from_evecharacter(1001)
        add_auth_character_to_user(user_1, 1002)
        user_2, co_1101 = create_user_from_evecharacter(1101)

        # re-add auth character 1002 to another user, but without member audit scopes
        add_auth_character_to_user(user_2, 1002, scopes="publicData")

        out = StringIO()
        call_command("memberaudit_reset_characters", "--noinput", stdout=out)

        self.assertSetEqual(
            set(Character.objects.values_list("character_ownership_id", flat=True)),
            {co_1001.id, co_1101.id},
        )


class TestDataExport(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_entities()
        cls.character = create_memberaudit_character(1001)

    def test_should_export_into_csv_file(self):
        # given
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
        out = StringIO()
        # when
        call_command("memberaudit_data_export", "wallet_journal", stdout=out)
        # then
        # ??
