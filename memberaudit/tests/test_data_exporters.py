import datetime as dt
import tempfile
from pathlib import Path

from pytz import utc

from django.test import TestCase

from ..core.data_exporters import export_topic_to_archive
from ..models import CharacterWalletJournalEntry
from . import create_memberaudit_character
from .testdata.load_entities import load_entities


class TestExportTopicToArchive(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_entities()
        cls.character = create_memberaudit_character(1001)

    def test_should_export_wallet_journal(self):
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
            first_party_id=1001,
            second_party_id=1002,
            reason="test reason",
        )
        # when
        with tempfile.TemporaryDirectory() as tmpdirname:
            result = export_topic_to_archive(
                topic="wallet-journal", destination_folder=tmpdirname
            )
            # then
            output_file = Path(result)
            self.assertTrue(output_file.exists())
            self.assertEqual("memberaudit_wallet-journal.zip", output_file.name)
