import csv
import datetime as dt
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from pytz import utc

from django.core.management import call_command
from eveuniverse.models import EveEntity

from app_utils.testing import NoSocketsTestCase

from ..models import Character, CharacterWalletJournalEntry
from . import (
    add_auth_character_to_user,
    create_memberaudit_character,
    create_user_from_evecharacter_with_access,
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
        user, co_1001 = create_user_from_evecharacter_with_access(1001)
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
        user_1, co_1001 = create_user_from_evecharacter_with_access(1001)
        add_auth_character_to_user(user_1, 1002)
        user_2, co_1101 = create_user_from_evecharacter_with_access(1101)

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
            amount=1000000.0,
            balance=20000000.0,
            ref_type="test_ref",
            context_id_type=CharacterWalletJournalEntry.CONTEXT_ID_TYPE_UNDEFINED,
            date=dt.datetime(2021, 1, 1, 12, 30, tzinfo=utc),
            description="test description",
            first_party=EveEntity.objects.get(id=1001),
            second_party=EveEntity.objects.get(id=1002),
            reason="test reason",
        )
        out = StringIO()
        # when
        with tempfile.TemporaryDirectory() as tmpdirname:
            with patch("django.utils.timezone.now") as mock_now:
                mock_now.return_value = dt.datetime(2021, 12, 1, 12, 30, tzinfo=utc)
                call_command(
                    "memberaudit_data_export",
                    "wallet_journal",
                    "--destination",
                    tmpdirname,
                    stdout=out,
                )
            # then
            output_file = Path(tmpdirname) / Path(
                "memberaudit_wallet_journal_20211201.csv"
            )
            self.assertTrue(output_file.exists())
            with output_file.open("r") as csv_file:
                reader = csv.DictReader(csv_file)
                data = [row for row in reader]
            self.assertEqual(len(data), 1)
            obj = data[0]
            self.assertEqual(obj["date"], "2021-01-01 12:30:00")
            self.assertEqual(obj["owner character"], "Bruce Wayne")
            self.assertEqual(obj["owner corporation"], "Wayne Technologies")
            self.assertEqual(obj["ref type"], "Test Ref")
            self.assertEqual(obj["first party"], "Bruce Wayne")
            self.assertEqual(obj["second party"], "Clark Kent")
            self.assertEqual(obj["amount"], "1000000.0")
            self.assertEqual(obj["balance"], "20000000.0")
            self.assertEqual(obj["description"], "test description")
            self.assertEqual(obj["reason"], "test reason")
