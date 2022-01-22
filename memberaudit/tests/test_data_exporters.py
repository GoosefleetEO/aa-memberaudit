import datetime as dt
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from pytz import utc

from django.test import TestCase

from ..core.data_exporters import export_topic_to_archive, file_to_zip
from ..models import (
    CharacterContract,
    CharacterContractItem,
    CharacterWalletJournalEntry,
)
from . import create_memberaudit_character
from .testdata.load_entities import load_entities
from .testdata.load_eveuniverse import load_eveuniverse


class TestExportTopicToArchive(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_entities()
        load_eveuniverse()
        cls.character = create_memberaudit_character(1001)

    def test_should_export_contract(self):
        # given
        contract = CharacterContract.objects.create(
            character=self.character,
            contract_id=42,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_ITEM_EXCHANGE,
            assignee_id=1002,
            date_issued=dt.datetime(2021, 1, 1, 12, 30, tzinfo=utc),
            date_expired=dt.datetime(2021, 1, 4, 12, 30, tzinfo=utc),
            for_corporation=False,
            issuer_id=1001,
            issuer_corporation_id=2001,
            status=CharacterContract.STATUS_OUTSTANDING,
            title="Dummy info",
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=1,
            is_included=True,
            is_singleton=False,
            quantity=1,
            eve_type_id=603,
        )
        # when
        with TemporaryDirectory() as tmpdirname:
            result = export_topic_to_archive(
                topic="contract", destination_folder=tmpdirname
            )
            # then
            output_file = Path(result)
            self.assertTrue(output_file.exists())
            self.assertEqual("memberaudit_contract.zip", output_file.name)

    def test_should_export_contract_item(self):
        # given
        contract = CharacterContract.objects.create(
            character=self.character,
            contract_id=42,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_ITEM_EXCHANGE,
            assignee_id=1002,
            date_issued=dt.datetime(2021, 1, 1, 12, 30, tzinfo=utc),
            date_expired=dt.datetime(2021, 1, 4, 12, 30, tzinfo=utc),
            for_corporation=False,
            issuer_id=1001,
            issuer_corporation_id=2001,
            status=CharacterContract.STATUS_OUTSTANDING,
            title="Dummy info",
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=1,
            is_included=True,
            is_singleton=False,
            quantity=1,
            eve_type_id=603,
        )
        # when
        with TemporaryDirectory() as tmpdirname:
            result = export_topic_to_archive(
                topic="contract-item", destination_folder=tmpdirname
            )
            # then
            output_file = Path(result)
            self.assertTrue(output_file.exists())
            self.assertEqual("memberaudit_contract-item.zip", output_file.name)

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
        with TemporaryDirectory() as tmpdirname:
            result = export_topic_to_archive(
                topic="wallet-journal", destination_folder=tmpdirname
            )
            # then
            output_file = Path(result)
            self.assertTrue(output_file.exists())
            self.assertEqual("memberaudit_wallet-journal.zip", output_file.name)


class TestZipFile(TestCase):
    def test_should_zip_file_into_archive(self):
        with TemporaryDirectory() as tmpdirname_1, TemporaryDirectory() as tmpdirname_2:
            # given
            source_file = Path(tmpdirname_1) / "test.csv"
            with source_file.open("w") as fp:
                fp.write("test file")
            destination = Path(tmpdirname_2)
            # when
            zip_file = file_to_zip(source_file, destination)
            # then
            with ZipFile(zip_file, "r") as myzip:
                namelist = myzip.namelist()
            self.assertIn(source_file.name, namelist)
