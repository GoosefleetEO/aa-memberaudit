import datetime as dt
from unittest.mock import patch

from bravado.exception import HTTPNotFound
from pytz import utc

from django.test import TestCase, override_settings
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from eveuniverse.models import EveEntity, EveSolarSystem, EveType

from app_utils.esi import EsiStatus
from app_utils.esi_testing import BravadoResponseStub
from app_utils.testing import NoSocketsTestCase

from ..core.xml_converter import eve_xml_to_html
from ..models import (
    Character,
    CharacterAttributes,
    CharacterContact,
    CharacterContactLabel,
    CharacterContract,
    CharacterContractBid,
    CharacterDetails,
    CharacterMail,
    CharacterMailLabel,
    CharacterSkill,
    CharacterWalletJournalEntry,
    Location,
    MailEntity,
)
from .testdata.esi_client_stub import esi_client_stub
from .testdata.load_entities import load_entities
from .testdata.load_eveuniverse import load_eveuniverse
from .testdata.load_locations import load_locations
from .utils import create_memberaudit_character

MODELS_PATH = "memberaudit.models"
MANAGERS_PATH = "memberaudit.managers"
TASKS_PATH = "memberaudit.tasks"


class CharacterUpdateTestDataMixin:
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()
        load_entities()
        load_locations()
        cls.character_1001 = create_memberaudit_character(1001)
        cls.character_1002 = create_memberaudit_character(1002)
        cls.corporation_2001 = EveEntity.objects.get(id=2001)
        cls.corporation_2002 = EveEntity.objects.get(id=2002)
        cls.token = cls.character_1001.character_ownership.user.token_set.first()
        cls.jita = EveSolarSystem.objects.get(id=30000142)
        cls.jita_44 = Location.objects.get(id=60003760)
        cls.amamake = EveSolarSystem.objects.get(id=30002537)
        cls.structure_1 = Location.objects.get(id=1000000000001)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateContacts(CharacterUpdateTestDataMixin, NoSocketsTestCase):
    def test_update_contact_labels_1(self, mock_esi):
        """can create new contact labels from scratch"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_contact_labels()
        self.assertEqual(self.character_1001.contact_labels.count(), 2)

        label = self.character_1001.contact_labels.get(label_id=1)
        self.assertEqual(label.name, "friend")

        label = self.character_1001.contact_labels.get(label_id=2)
        self.assertEqual(label.name, "pirate")

    def test_update_contact_labels_2(self, mock_esi):
        """can remove obsolete labels"""
        mock_esi.client = esi_client_stub
        CharacterContactLabel.objects.create(
            character=self.character_1001, label_id=99, name="Obsolete"
        )

        self.character_1001.update_contact_labels()
        self.assertEqual(
            {x.label_id for x in self.character_1001.contact_labels.all()}, {1, 2}
        )

    def test_update_contact_labels_3(self, mock_esi):
        """can update existing labels"""
        mock_esi.client = esi_client_stub
        CharacterContactLabel.objects.create(
            character=self.character_1001, label_id=1, name="Obsolete"
        )

        self.character_1001.update_contact_labels()
        self.assertEqual(
            {x.label_id for x in self.character_1001.contact_labels.all()}, {1, 2}
        )

        label = self.character_1001.contact_labels.get(label_id=1)
        self.assertEqual(label.name, "friend")

    def test_update_contact_labels_4(self, mock_esi):
        """when data from ESI has not changed, then skip update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_contact_labels()
        label = self.character_1001.contact_labels.get(label_id=1)
        label.name = "foe"
        label.save()

        self.character_1001.update_contact_labels()

        self.assertEqual(self.character_1001.contact_labels.count(), 2)
        label = self.character_1001.contact_labels.get(label_id=1)
        self.assertEqual(label.name, "foe")

    def test_update_contact_labels_5(self, mock_esi):
        """when data from ESI has not changed and update is forced, then do update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_contact_labels()
        label = self.character_1001.contact_labels.get(label_id=1)
        label.name = "foe"
        label.save()

        self.character_1001.update_contact_labels(force_update=True)

        self.assertEqual(self.character_1001.contact_labels.count(), 2)
        label = self.character_1001.contact_labels.get(label_id=1)
        self.assertEqual(label.name, "friend")

    def test_update_contacts_1(self, mock_esi):
        """can create contacts"""
        mock_esi.client = esi_client_stub
        CharacterContactLabel.objects.create(
            character=self.character_1001, label_id=1, name="friend"
        )
        CharacterContactLabel.objects.create(
            character=self.character_1001, label_id=2, name="pirate"
        )

        self.character_1001.update_contacts()

        self.assertEqual(self.character_1001.contacts.count(), 2)

        obj = self.character_1001.contacts.get(eve_entity_id=1101)
        self.assertEqual(obj.eve_entity.category, EveEntity.CATEGORY_CHARACTER)
        self.assertFalse(obj.is_blocked)
        self.assertTrue(obj.is_watched)
        self.assertEqual(obj.standing, -10)
        self.assertEqual({x.label_id for x in obj.labels.all()}, {2})

        obj = self.character_1001.contacts.get(eve_entity_id=2002)
        self.assertEqual(obj.eve_entity.category, EveEntity.CATEGORY_CORPORATION)
        self.assertFalse(obj.is_blocked)
        self.assertFalse(obj.is_watched)
        self.assertEqual(obj.standing, 5)
        self.assertEqual(obj.labels.count(), 0)

    def test_update_contacts_2(self, mock_esi):
        """can remove obsolete contacts"""
        mock_esi.client = esi_client_stub
        CharacterContactLabel.objects.create(
            character=self.character_1001, label_id=1, name="friend"
        )
        CharacterContactLabel.objects.create(
            character=self.character_1001, label_id=2, name="pirate"
        )
        CharacterContact.objects.create(
            character=self.character_1001,
            eve_entity=EveEntity.objects.get(id=3101),
            standing=-5,
        )

        self.character_1001.update_contacts()

        self.assertEqual(
            {x.eve_entity_id for x in self.character_1001.contacts.all()}, {1101, 2002}
        )

    def test_update_contacts_3(self, mock_esi):
        """can update existing contacts"""
        mock_esi.client = esi_client_stub
        CharacterContactLabel.objects.create(
            character=self.character_1001, label_id=2, name="pirate"
        )
        my_label = CharacterContactLabel.objects.create(
            character=self.character_1001, label_id=1, name="Dummy"
        )
        my_contact = CharacterContact.objects.create(
            character=self.character_1001,
            eve_entity=EveEntity.objects.get(id=1101),
            is_blocked=True,
            is_watched=False,
            standing=-5,
        )
        my_contact.labels.add(my_label)

        self.character_1001.update_contacts()

        obj = self.character_1001.contacts.get(eve_entity_id=1101)
        self.assertEqual(obj.eve_entity.category, EveEntity.CATEGORY_CHARACTER)
        self.assertFalse(obj.is_blocked)
        self.assertTrue(obj.is_watched)
        self.assertEqual(obj.standing, -10)
        self.assertEqual({x.label_id for x in obj.labels.all()}, {2})

    def test_update_contacts_4(self, mock_esi):
        """when ESI data has not changed, then skip update"""
        mock_esi.client = esi_client_stub
        CharacterContactLabel.objects.create(
            character=self.character_1001, label_id=1, name="friend"
        )
        CharacterContactLabel.objects.create(
            character=self.character_1001, label_id=2, name="pirate"
        )

        self.character_1001.update_contacts()
        obj = self.character_1001.contacts.get(eve_entity_id=1101)
        obj.is_watched = False
        obj.save()

        self.character_1001.update_contacts()

        obj = self.character_1001.contacts.get(eve_entity_id=1101)
        self.assertFalse(obj.is_watched)

    def test_update_contacts_5(self, mock_esi):
        """when ESI data has not changed and update is forced, then update"""
        mock_esi.client = esi_client_stub
        CharacterContactLabel.objects.create(
            character=self.character_1001, label_id=1, name="friend"
        )
        CharacterContactLabel.objects.create(
            character=self.character_1001, label_id=2, name="pirate"
        )

        self.character_1001.update_contacts()
        obj = self.character_1001.contacts.get(eve_entity_id=1101)
        obj.is_watched = False
        obj.save()

        self.character_1001.update_contacts(force_update=True)

        obj = self.character_1001.contacts.get(eve_entity_id=1101)
        self.assertTrue(obj.is_watched)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateContracts(CharacterUpdateTestDataMixin, NoSocketsTestCase):
    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    def test_update_contracts_1(self, mock_esi):
        """can create new courier contract"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_contract_headers()
        self.assertSetEqual(
            set(self.character_1001.contracts.values_list("contract_id", flat=True)),
            {100000001, 100000002, 100000003},
        )

        obj = self.character_1001.contracts.get(contract_id=100000001)
        self.assertEqual(obj.contract_type, CharacterContract.TYPE_COURIER)
        self.assertEqual(obj.acceptor, EveEntity.objects.get(id=1101))
        self.assertEqual(obj.assignee, EveEntity.objects.get(id=2101))
        self.assertEqual(obj.availability, CharacterContract.AVAILABILITY_PERSONAL)
        self.assertIsNone(obj.buyout)
        self.assertEqual(float(obj.collateral), 550000000.0)
        self.assertEqual(obj.date_accepted, parse_datetime("2019-10-06T13:15:21Z"))
        self.assertEqual(obj.date_completed, parse_datetime("2019-10-07T13:15:21Z"))
        self.assertEqual(obj.date_expired, parse_datetime("2019-10-09T13:15:21Z"))
        self.assertEqual(obj.date_issued, parse_datetime("2019-10-02T13:15:21Z"))
        self.assertEqual(obj.days_to_complete, 3)
        self.assertEqual(obj.end_location, self.structure_1)
        self.assertFalse(obj.for_corporation)
        self.assertEqual(obj.issuer_corporation, EveEntity.objects.get(id=2001))
        self.assertEqual(obj.issuer, EveEntity.objects.get(id=1001))
        self.assertEqual(float(obj.price), 0.0)
        self.assertEqual(float(obj.reward), 500000000.0)
        self.assertEqual(obj.start_location, self.jita_44)
        self.assertEqual(obj.status, CharacterContract.STATUS_IN_PROGRESS)
        self.assertEqual(obj.title, "Test 1")
        self.assertEqual(obj.volume, 486000.0)

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    def test_update_contracts_2(self, mock_esi):
        """can create new item exchange contract"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_contract_headers()
        obj = self.character_1001.contracts.get(contract_id=100000002)
        self.assertEqual(obj.contract_type, CharacterContract.TYPE_ITEM_EXCHANGE)
        self.assertEqual(float(obj.price), 270000000.0)
        self.assertEqual(obj.volume, 486000.0)
        self.assertEqual(obj.status, CharacterContract.STATUS_FINISHED)

        self.character_1001.update_contract_items(contract=obj)

        self.assertEqual(obj.items.count(), 2)

        item = obj.items.get(record_id=1)
        self.assertTrue(item.is_included)
        self.assertFalse(item.is_singleton)
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.eve_type, EveType.objects.get(id=19540))

        item = obj.items.get(record_id=2)
        self.assertTrue(item.is_included)
        self.assertFalse(item.is_singleton)
        self.assertEqual(item.quantity, 5)
        self.assertEqual(item.raw_quantity, -1)
        self.assertEqual(item.eve_type, EveType.objects.get(id=19551))

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    def test_update_contracts_3(self, mock_esi):
        """can create new auction contract"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_contract_headers()
        obj = self.character_1001.contracts.get(contract_id=100000003)
        self.assertEqual(obj.contract_type, CharacterContract.TYPE_AUCTION)
        self.assertEqual(float(obj.buyout), 200_000_000.0)
        self.assertEqual(float(obj.price), 20_000_000.0)
        self.assertEqual(obj.volume, 400.0)
        self.assertEqual(obj.status, CharacterContract.STATUS_OUTSTANDING)

        self.character_1001.update_contract_items(contract=obj)

        self.assertEqual(obj.items.count(), 1)
        item = obj.items.get(record_id=1)
        self.assertTrue(item.is_included)
        self.assertFalse(item.is_singleton)
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.eve_type, EveType.objects.get(id=19540))

        self.character_1001.update_contract_bids(contract=obj)

        self.assertEqual(obj.bids.count(), 1)
        bid = obj.bids.get(bid_id=1)
        self.assertEqual(float(bid.amount), 1_000_000.23)
        self.assertEqual(bid.date_bid, parse_datetime("2017-01-01T10:10:10Z"))
        self.assertEqual(bid.bidder, EveEntity.objects.get(id=1101))

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    def test_update_contracts_4(self, mock_esi):
        """old contracts must be kept"""
        mock_esi.client = esi_client_stub

        CharacterContract.objects.create(
            character=self.character_1001,
            contract_id=190000001,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_COURIER,
            assignee=EveEntity.objects.get(id=1002),
            date_issued=now() - dt.timedelta(days=60),
            date_expired=now() - dt.timedelta(days=30),
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_IN_PROGRESS,
            start_location=self.jita_44,
            end_location=self.structure_1,
            title="Old contract",
        )

        self.character_1001.update_contract_headers()
        self.assertEqual(self.character_1001.contracts.count(), 4)

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    def test_update_contracts_5(self, mock_esi):
        """Existing contracts are updated"""
        mock_esi.client = esi_client_stub

        CharacterContract.objects.create(
            character=self.character_1001,
            contract_id=100000001,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_COURIER,
            assignee=EveEntity.objects.get(id=2101),
            date_issued=parse_datetime("2019-10-02T13:15:21Z"),
            date_expired=parse_datetime("2019-10-09T13:15:21Z"),
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_OUTSTANDING,
            start_location=self.jita_44,
            end_location=self.structure_1,
            title="Test 1",
            collateral=550000000,
            reward=500000000,
            volume=486000,
            days_to_complete=3,
        )

        self.character_1001.update_contract_headers()

        obj = self.character_1001.contracts.get(contract_id=100000001)
        self.assertEqual(obj.contract_type, CharacterContract.TYPE_COURIER)
        self.assertEqual(obj.acceptor, EveEntity.objects.get(id=1101))
        self.assertEqual(obj.assignee, EveEntity.objects.get(id=2101))
        self.assertEqual(obj.availability, CharacterContract.AVAILABILITY_PERSONAL)
        self.assertIsNone(obj.buyout)
        self.assertEqual(float(obj.collateral), 550000000.0)
        self.assertEqual(obj.date_accepted, parse_datetime("2019-10-06T13:15:21Z"))
        self.assertEqual(obj.date_completed, parse_datetime("2019-10-07T13:15:21Z"))
        self.assertEqual(obj.date_expired, parse_datetime("2019-10-09T13:15:21Z"))
        self.assertEqual(obj.date_issued, parse_datetime("2019-10-02T13:15:21Z"))
        self.assertEqual(obj.days_to_complete, 3)
        self.assertEqual(obj.end_location, self.structure_1)
        self.assertFalse(obj.for_corporation)
        self.assertEqual(obj.issuer_corporation, EveEntity.objects.get(id=2001))
        self.assertEqual(obj.issuer, EveEntity.objects.get(id=1001))
        self.assertEqual(float(obj.reward), 500000000.0)
        self.assertEqual(obj.start_location, self.jita_44)
        self.assertEqual(obj.status, CharacterContract.STATUS_IN_PROGRESS)
        self.assertEqual(obj.title, "Test 1")
        self.assertEqual(obj.volume, 486000.0)

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    def test_update_contracts_6(self, mock_esi):
        """can add new bids to auction contract"""
        mock_esi.client = esi_client_stub
        contract = CharacterContract.objects.create(
            character=self.character_1001,
            contract_id=100000003,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_AUCTION,
            assignee=EveEntity.objects.get(id=2101),
            date_issued=parse_datetime("2019-10-02T13:15:21Z"),
            date_expired=parse_datetime("2019-10-09T13:15:21Z"),
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_OUTSTANDING,
            start_location=self.jita_44,
            end_location=self.jita_44,
            buyout=200_000_000,
            price=20_000_000,
            volume=400,
        )
        CharacterContractBid.objects.create(
            contract=contract,
            bid_id=2,
            amount=21_000_000,
            bidder=EveEntity.objects.get(id=1003),
            date_bid=now(),
        )

        self.character_1001.update_contract_headers()
        obj = self.character_1001.contracts.get(contract_id=100000003)
        self.character_1001.update_contract_bids(contract=obj)

        self.assertEqual(obj.bids.count(), 2)

        bid = obj.bids.get(bid_id=1)
        self.assertEqual(float(bid.amount), 1_000_000.23)
        self.assertEqual(bid.date_bid, parse_datetime("2017-01-01T10:10:10Z"))
        self.assertEqual(bid.bidder, EveEntity.objects.get(id=1101))

        bid = obj.bids.get(bid_id=2)
        self.assertEqual(float(bid.amount), 21_000_000)

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    def test_update_contracts_7(self, mock_esi):
        """when contract list from ESI has not changed, then skip update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_contract_headers()
        obj = self.character_1001.contracts.get(contract_id=100000001)
        obj.status = CharacterContract.STATUS_FINISHED
        obj.save()

        self.character_1001.update_contract_headers()

        obj = self.character_1001.contracts.get(contract_id=100000001)
        self.assertEqual(obj.status, CharacterContract.STATUS_FINISHED)

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    def test_update_contracts_8(self, mock_esi):
        """
        when contract list from ESI has not changed and update is forced, then update
        """
        mock_esi.client = esi_client_stub

        self.character_1001.update_contract_headers()
        obj = self.character_1001.contracts.get(contract_id=100000001)
        obj.status = CharacterContract.STATUS_FINISHED
        obj.save()

        self.character_1001.update_contract_headers(force_update=True)

        obj = self.character_1001.contracts.get(contract_id=100000001)
        self.assertEqual(obj.status, CharacterContract.STATUS_IN_PROGRESS)

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", 10)
    def test_update_contracts_9(self, mock_esi):
        """when retention limit is set, then only create contracts younger than limit"""
        mock_esi.client = esi_client_stub

        with patch(MODELS_PATH + ".character.now") as mock_now:
            mock_now.return_value = dt.datetime(2019, 10, 21, 1, 15, tzinfo=utc)
            self.character_1001.update_contract_headers()

        self.assertSetEqual(
            set(self.character_1001.contracts.values_list("contract_id", flat=True)),
            {100000002, 100000003},
        )

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", 15)
    def test_update_contracts_10(self, mock_esi):
        """when retention limit is set,
        then remove existing contracts older than limit
        """
        mock_esi.client = esi_client_stub
        CharacterContract.objects.create(
            character=self.character_1001,
            contract_id=100000004,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_COURIER,
            assignee=EveEntity.objects.get(id=2101),
            date_issued=parse_datetime("2019-09-02T13:15:21Z"),
            date_expired=parse_datetime("2019-09-09T13:15:21Z"),
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_OUTSTANDING,
            start_location=self.jita_44,
            end_location=self.structure_1,
            title="This contract is too old",
            collateral=550000000,
            reward=500000000,
            volume=486000,
            days_to_complete=3,
        )

        with patch(MODELS_PATH + ".character.now") as mock_now:
            mock_now.return_value = dt.datetime(2019, 10, 21, 1, 15, tzinfo=utc)
            self.character_1001.update_contract_headers()

        self.assertSetEqual(
            set(self.character_1001.contracts.values_list("contract_id", flat=True)),
            {100000001, 100000002, 100000003},
        )


@patch(MANAGERS_PATH + ".sections.eve_xml_to_html")
@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateCharacterDetails(
    CharacterUpdateTestDataMixin, NoSocketsTestCase
):
    def test_can_create_from_scratch(self, mock_esi, mock_eve_xml_to_html):
        # given
        mock_esi.client = esi_client_stub
        mock_eve_xml_to_html.side_effect = lambda x: eve_xml_to_html(x)
        # when
        self.character_1001.update_character_details()
        # then
        self.assertEqual(self.character_1001.details.eve_ancestry.id, 11)
        self.assertEqual(
            self.character_1001.details.birthday, parse_datetime("2015-03-24T11:37:00Z")
        )
        self.assertEqual(self.character_1001.details.eve_bloodline_id, 1)
        self.assertEqual(self.character_1001.details.corporation, self.corporation_2001)
        self.assertEqual(self.character_1001.details.description, "Scio me nihil scire")
        self.assertEqual(
            self.character_1001.details.gender, CharacterDetails.GENDER_MALE
        )
        self.assertEqual(self.character_1001.details.name, "Bruce Wayne")
        self.assertEqual(self.character_1001.details.eve_race.id, 1)
        self.assertEqual(
            self.character_1001.details.title, "All round pretty awesome guy"
        )
        self.assertTrue(mock_eve_xml_to_html.called)

    def test_can_update_existing_data(self, mock_esi, mock_eve_xml_to_html):
        # given
        mock_esi.client = esi_client_stub
        mock_eve_xml_to_html.side_effect = lambda x: eve_xml_to_html(x)
        CharacterDetails.objects.create(
            character=self.character_1001,
            birthday=now(),
            corporation=self.corporation_2002,
            description="Change me",
            eve_bloodline_id=1,
            eve_race_id=1,
            name="Change me also",
        )
        # when
        self.character_1001.update_character_details()
        # then
        self.character_1001.details.refresh_from_db()
        self.assertEqual(self.character_1001.details.eve_ancestry_id, 11)
        self.assertEqual(
            self.character_1001.details.birthday, parse_datetime("2015-03-24T11:37:00Z")
        )
        self.assertEqual(self.character_1001.details.eve_bloodline_id, 1)
        self.assertEqual(self.character_1001.details.corporation, self.corporation_2001)
        self.assertEqual(self.character_1001.details.description, "Scio me nihil scire")
        self.assertEqual(
            self.character_1001.details.gender, CharacterDetails.GENDER_MALE
        )
        self.assertEqual(self.character_1001.details.name, "Bruce Wayne")
        self.assertEqual(self.character_1001.details.eve_race.id, 1)
        self.assertEqual(
            self.character_1001.details.title, "All round pretty awesome guy"
        )
        self.assertTrue(mock_eve_xml_to_html.called)

    def test_skip_update_1(self, mock_esi, mock_eve_xml_to_html):
        """when data from ESI has not changed, then skip update"""
        # given
        mock_esi.client = esi_client_stub
        mock_eve_xml_to_html.side_effect = lambda x: eve_xml_to_html(x)
        self.character_1001.update_character_details()
        self.character_1001.details.name = "John Doe"
        self.character_1001.details.save()
        # when
        self.character_1001.update_character_details()
        # then
        self.character_1001.details.refresh_from_db()
        self.assertEqual(self.character_1001.details.name, "John Doe")

    def test_skip_update_2(self, mock_esi, mock_eve_xml_to_html):
        """when data from ESI has not changed and update is forced, then do update"""
        # given
        mock_esi.client = esi_client_stub
        mock_eve_xml_to_html.side_effect = lambda x: eve_xml_to_html(x)
        self.character_1001.update_character_details()
        self.character_1001.details.name = "John Doe"
        self.character_1001.details.save()
        # when
        self.character_1001.update_character_details(force_update=True)
        # then
        self.character_1001.details.refresh_from_db()
        self.assertEqual(self.character_1001.details.name, "Bruce Wayne")

    def test_can_handle_u_bug_1(self, mock_esi, mock_eve_xml_to_html):
        # given
        mock_esi.client = esi_client_stub
        mock_eve_xml_to_html.side_effect = lambda x: eve_xml_to_html(x)
        # when
        self.character_1002.update_character_details()
        # then
        self.assertNotEqual(self.character_1002.details.description[:2], "u'")

    def test_can_handle_u_bug_2(self, mock_esi, mock_eve_xml_to_html):
        # given
        mock_esi.client = esi_client_stub
        mock_eve_xml_to_html.side_effect = lambda x: eve_xml_to_html(x)
        character = create_memberaudit_character(1003)
        # when
        character.update_character_details()
        # then
        self.assertNotEqual(character.details.description[:2], "u'")

    def test_can_handle_u_bug_3(self, mock_esi, mock_eve_xml_to_html):
        # given
        mock_esi.client = esi_client_stub
        mock_eve_xml_to_html.side_effect = lambda x: eve_xml_to_html(x)
        character = create_memberaudit_character(1101)
        # when
        character.update_character_details()
        # then
        self.assertNotEqual(character.details.description[:2], "u'")

    # @patch(MANAGERS_PATH + ".sections.get_or_create_esi_or_none")
    # def test_esi_ancestry_bug(
    #     self, mock_get_or_create_esi_or_none, mock_esi, mock_eve_xml_to_html
    # ):
    #     """when esi ancestry endpoint returns http error then ignore it and carry on"""

    #     def my_get_or_create_esi_or_none(prop_name: str, dct: dict, Model: type):
    #         if issubclass(Model, EveAncestry):
    #             raise HTTPInternalServerError(
    #                 response=BravadoResponseStub(500, "Test exception")
    #             )
    #         return get_or_create_esi_or_none(prop_name=prop_name, dct=dct, Model=Model)

    #     mock_esi.client = esi_client_stub
    #     mock_eve_xml_to_html.side_effect = lambda x: eve_xml_to_html(x)
    #     mock_get_or_create_esi_or_none.side_effect = my_get_or_create_esi_or_none

    #     self.character_1001.update_character_details()
    #     self.assertIsNone(self.character_1001.details.eve_ancestry)
    #     self.assertEqual(
    #         self.character_1001.details.birthday, parse_datetime("2015-03-24T11:37:00Z")
    #     )
    #     self.assertEqual(self.character_1001.details.eve_bloodline_id, 1)
    #     self.assertEqual(self.character_1001.details.corporation, self.corporation_2001)
    #     self.assertEqual(self.character_1001.details.description, "Scio me nihil scire")
    #     self.assertEqual(
    #         self.character_1001.details.gender, CharacterDetails.GENDER_MALE
    #     )
    #     self.assertEqual(self.character_1001.details.name, "Bruce Wayne")
    #     self.assertEqual(self.character_1001.details.eve_race.id, 1)
    #     self.assertEqual(
    #         self.character_1001.details.title, "All round pretty awesome guy"
    #     )
    #     self.assertTrue(mock_eve_xml_to_html.called)


@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateCorporationHistory(
    CharacterUpdateTestDataMixin, NoSocketsTestCase
):
    def test_create(self, mock_esi):
        """can create corporation history from scratch"""
        mock_esi.client = esi_client_stub
        self.character_1001.update_corporation_history()
        self.assertEqual(self.character_1001.corporation_history.count(), 2)

        obj = self.character_1001.corporation_history.get(record_id=500)
        self.assertEqual(obj.corporation, self.corporation_2001)
        self.assertTrue(obj.is_deleted)
        self.assertEqual(obj.start_date, parse_datetime("2016-06-26T20:00:00Z"))

        obj = self.character_1001.corporation_history.get(record_id=501)
        self.assertEqual(obj.corporation, self.corporation_2002)
        self.assertFalse(obj.is_deleted)
        self.assertEqual(obj.start_date, parse_datetime("2016-07-26T20:00:00Z"))

    def test_update_1(self, mock_esi):
        """can update existing corporation history"""
        mock_esi.client = esi_client_stub
        self.character_1001.corporation_history.create(
            record_id=500, corporation=self.corporation_2002, start_date=now()
        )

        self.character_1001.update_corporation_history()
        self.assertEqual(self.character_1001.corporation_history.count(), 2)

        obj = self.character_1001.corporation_history.get(record_id=500)
        self.assertEqual(obj.corporation, self.corporation_2001)
        self.assertTrue(obj.is_deleted)
        self.assertEqual(obj.start_date, parse_datetime("2016-06-26T20:00:00Z"))

    def test_update_2(self, mock_esi):
        """when data from ESI has not changed, then skip update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_corporation_history()
        obj = self.character_1001.corporation_history.get(record_id=500)
        obj.corporation = self.corporation_2002
        obj.save()

        self.character_1001.update_corporation_history()
        obj = self.character_1001.corporation_history.get(record_id=500)
        self.assertEqual(obj.corporation, self.corporation_2002)

    def test_update_3(self, mock_esi):
        """when data from ESI has not changed and update is forced, then do update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_corporation_history()
        obj = self.character_1001.corporation_history.get(record_id=500)
        obj.corporation = self.corporation_2002
        obj.save()

        self.character_1001.update_corporation_history(force_update=True)

        obj = self.character_1001.corporation_history.get(record_id=500)
        self.assertEqual(obj.corporation, self.corporation_2001)


@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateImplants(CharacterUpdateTestDataMixin, NoSocketsTestCase):
    def test_update_implants_1(self, mock_esi):
        """can create implants from scratch"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_implants()
        self.assertEqual(self.character_1001.implants.count(), 3)
        self.assertSetEqual(
            set(self.character_1001.implants.values_list("eve_type_id", flat=True)),
            {19540, 19551, 19553},
        )

    def test_update_implants_2(self, mock_esi):
        """can deal with no implants returned from ESI"""
        mock_esi.client = esi_client_stub

        self.character_1002.update_implants()
        self.assertEqual(self.character_1002.implants.count(), 0)

    def test_update_implants_3(self, mock_esi):
        """when data from ESI has not changed, then skip update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_implants()
        self.character_1001.implants.get(eve_type_id=19540).delete()

        self.character_1001.update_implants()
        self.assertFalse(
            self.character_1001.implants.filter(eve_type_id=19540).exists()
        )

    def test_update_implants_4(self, mock_esi):
        """when data from ESI has not changed and update is forced, then do update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_implants()
        self.character_1001.implants.get(eve_type_id=19540).delete()

        self.character_1001.update_implants(force_update=True)
        self.assertTrue(self.character_1001.implants.filter(eve_type_id=19540).exists())


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateJumpClones(CharacterUpdateTestDataMixin, NoSocketsTestCase):
    def test_update_jump_clones_1(self, mock_esi):
        """can update jump clones with implants"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_jump_clones()
        self.assertEqual(self.character_1001.jump_clones.count(), 1)

        obj = self.character_1001.jump_clones.get(jump_clone_id=12345)
        self.assertEqual(obj.location, self.jita_44)
        self.assertEqual(
            {x for x in obj.implants.values_list("eve_type", flat=True)},
            {19540, 19551, 19553},
        )

    def test_update_jump_clones_2(self, mock_esi):
        """can update jump clones without implants"""
        mock_esi.client = esi_client_stub

        self.character_1002.update_jump_clones()
        self.assertEqual(self.character_1002.jump_clones.count(), 1)

        obj = self.character_1002.jump_clones.get(jump_clone_id=12345)
        self.assertEqual(obj.location, self.jita_44)
        self.assertEqual(obj.implants.count(), 0)

    def test_skip_update_1(self, mock_esi):
        """when ESI data has not changed, then skip update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_jump_clones()
        obj = self.character_1001.jump_clones.get(jump_clone_id=12345)
        obj.location = self.structure_1
        obj.save()

        self.character_1001.update_jump_clones()

        obj = self.character_1001.jump_clones.get(jump_clone_id=12345)
        self.assertEqual(obj.location, self.structure_1)

    def test_skip_update_2(self, mock_esi):
        """when ESI data has not changed and update is forced, then do update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_jump_clones()
        obj = self.character_1001.jump_clones.get(jump_clone_id=12345)
        obj.location = self.structure_1
        obj.save()

        self.character_1001.update_jump_clones(force_update=True)

        obj = self.character_1001.jump_clones.get(jump_clone_id=12345)
        self.assertEqual(obj.location, self.jita_44)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateMails(CharacterUpdateTestDataMixin, TestCase):
    def test_update_mailing_lists_1(self, mock_esi):
        """can create new mailing lists from scratch"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_mailing_lists()

        self.assertSetEqual(
            set(MailEntity.objects.values_list("id", flat=True)), {9001, 9002}
        )
        self.assertSetEqual(
            set(self.character_1001.mailing_lists.values_list("id", flat=True)),
            {9001, 9002},
        )

        obj = MailEntity.objects.get(id=9001)
        self.assertEqual(obj.name, "Dummy 1")

        obj = MailEntity.objects.get(id=9002)
        self.assertEqual(obj.name, "Dummy 2")

    def test_update_mailing_lists_2(self, mock_esi):
        """does not remove obsolete mailing lists"""
        mock_esi.client = esi_client_stub
        MailEntity.objects.create(
            id=5, category=MailEntity.Category.MAILING_LIST, name="Obsolete"
        )

        self.character_1001.update_mailing_lists()

        self.assertSetEqual(
            set(MailEntity.objects.values_list("id", flat=True)), {9001, 9002, 5}
        )
        self.assertSetEqual(
            set(self.character_1001.mailing_lists.values_list("id", flat=True)),
            {9001, 9002},
        )

    def test_update_mailing_lists_3(self, mock_esi):
        """updates existing mailing lists"""
        mock_esi.client = esi_client_stub
        MailEntity.objects.create(
            id=9001, category=MailEntity.Category.MAILING_LIST, name="Update me"
        )

        self.character_1001.update_mailing_lists()

        self.assertSetEqual(
            set(MailEntity.objects.values_list("id", flat=True)), {9001, 9002}
        )
        self.assertSetEqual(
            set(self.character_1001.mailing_lists.values_list("id", flat=True)),
            {9001, 9002},
        )
        obj = MailEntity.objects.get(id=9001)
        self.assertEqual(obj.name, "Dummy 1")

    def test_update_mailing_lists_4(self, mock_esi):
        """when data from ESI has not changed, then skip update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_mailing_lists()
        obj = MailEntity.objects.get(id=9001)
        obj.name = "Extravaganza"
        obj.save()
        self.character_1001.mailing_lists.clear()

        self.character_1001.update_mailing_lists()
        obj = MailEntity.objects.get(id=9001)
        self.assertEqual(obj.name, "Extravaganza")
        self.assertSetEqual(
            set(self.character_1001.mailing_lists.values_list("id", flat=True)), set()
        )

    def test_update_mailing_lists_5(self, mock_esi):
        """when data from ESI has not changed and update is forced, then do update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_mailing_lists()
        obj = MailEntity.objects.get(id=9001)
        obj.name = "Extravaganza"
        obj.save()

        self.character_1001.update_mailing_lists(force_update=True)
        obj = MailEntity.objects.get(id=9001)
        self.assertEqual(obj.name, "Dummy 1")

    def test_update_mail_labels_1(self, mock_esi):
        """can create from scratch"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_mail_labels()

        self.assertEqual(self.character_1001.unread_mail_count.total, 5)
        self.assertSetEqual(
            set(self.character_1001.mail_labels.values_list("label_id", flat=True)),
            {3, 17},
        )

        obj = self.character_1001.mail_labels.get(label_id=3)
        self.assertEqual(obj.name, "PINK")
        self.assertEqual(obj.unread_count, 4)
        self.assertEqual(obj.color, "#660066")

        obj = self.character_1001.mail_labels.get(label_id=17)
        self.assertEqual(obj.name, "WHITE")
        self.assertEqual(obj.unread_count, 1)
        self.assertEqual(obj.color, "#ffffff")

    def test_update_mail_labels_2(self, mock_esi):
        """will remove obsolete labels"""
        mock_esi.client = esi_client_stub
        CharacterMailLabel.objects.create(
            character=self.character_1001, label_id=666, name="Obsolete"
        )

        self.character_1001.update_mail_labels()

        self.assertSetEqual(
            set(self.character_1001.mail_labels.values_list("label_id", flat=True)),
            {3, 17},
        )

    def test_update_mail_labels_3(self, mock_esi):
        """will update existing labels"""
        mock_esi.client = esi_client_stub
        CharacterMailLabel.objects.create(
            character=self.character_1001,
            label_id=3,
            name="Update me",
            unread_count=0,
            color=0,
        )

        self.character_1001.update_mail_labels()

        self.assertSetEqual(
            set(self.character_1001.mail_labels.values_list("label_id", flat=True)),
            {3, 17},
        )

        obj = self.character_1001.mail_labels.get(label_id=3)
        self.assertEqual(obj.name, "PINK")
        self.assertEqual(obj.unread_count, 4)
        self.assertEqual(obj.color, "#660066")

    def test_update_mail_labels_4(self, mock_esi):
        """when data from ESI has not changed, then skip update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_mail_labels()
        obj = self.character_1001.mail_labels.get(label_id=3)
        obj.name = "MAGENTA"
        obj.save()

        self.character_1001.update_mail_labels()

        obj = self.character_1001.mail_labels.get(label_id=3)
        self.assertEqual(obj.name, "MAGENTA")

    def test_update_mail_labels_5(self, mock_esi):
        """when data from ESI has not changed and update is forced, then do update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_mail_labels()
        obj = self.character_1001.mail_labels.get(label_id=3)
        obj.name = "MAGENTA"
        obj.save()

        self.character_1001.update_mail_labels(force_update=True)

        obj = self.character_1001.mail_labels.get(label_id=3)
        self.assertEqual(obj.name, "PINK")

    @staticmethod
    def stub_eve_entity_get_or_create_esi(id, *args, **kwargs):
        """will return EveEntity if it exists else None, False"""
        try:
            obj = EveEntity.objects.get(id=id)
            return obj, True
        except EveEntity.DoesNotExist:
            return None, False

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    @patch(MANAGERS_PATH + ".general.fetch_esi_status")
    @patch(MANAGERS_PATH + ".sections.EveEntity.objects.get_or_create_esi")
    def test_update_mail_headers_1(
        self, mock_eve_entity, mock_fetch_esi_status, mock_esi
    ):
        """can create new mail from scratch"""
        mock_esi.client = esi_client_stub
        mock_eve_entity.side_effect = self.stub_eve_entity_get_or_create_esi
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)

        self.character_1001.update_mailing_lists()
        self.character_1001.update_mail_labels()
        self.character_1001.update_mail_headers()
        self.assertSetEqual(
            set(self.character_1001.mails.values_list("mail_id", flat=True)),
            {1, 2, 3},
        )

        obj = self.character_1001.mails.get(mail_id=1)
        self.assertEqual(obj.sender.id, 1002)
        self.assertTrue(obj.is_read)
        self.assertEqual(obj.subject, "Mail 1")
        self.assertEqual(obj.timestamp, parse_datetime("2015-09-05T16:07:00Z"))
        self.assertFalse(obj.body)
        self.assertTrue(obj.recipients.filter(id=1001).exists())
        self.assertTrue(obj.recipients.filter(id=9001).exists())
        self.assertSetEqual(set(obj.labels.values_list("label_id", flat=True)), {3})

        obj = self.character_1001.mails.get(mail_id=2)
        self.assertEqual(obj.sender_id, 9001)
        self.assertFalse(obj.is_read)
        self.assertEqual(obj.subject, "Mail 2")
        self.assertEqual(obj.timestamp, parse_datetime("2015-09-10T18:07:00Z"))
        self.assertFalse(obj.body)
        self.assertSetEqual(set(obj.labels.values_list("label_id", flat=True)), {3})

        obj = self.character_1001.mails.get(mail_id=3)
        self.assertEqual(obj.sender_id, 1002)
        self.assertTrue(obj.recipients.filter(id=9003).exists())
        self.assertEqual(obj.timestamp, parse_datetime("2015-09-20T12:07:00Z"))

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    @patch(MANAGERS_PATH + ".general.fetch_esi_status")
    @patch(MANAGERS_PATH + ".sections.EveEntity.objects.get_or_create_esi")
    def test_update_mail_headers_2(
        self, mock_eve_entity, mock_fetch_esi_status, mock_esi
    ):
        """can update existing mail"""
        mock_esi.client = esi_client_stub
        mock_eve_entity.side_effect = self.stub_eve_entity_get_or_create_esi
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        sender, _ = MailEntity.objects.update_or_create_from_eve_entity_id(id=1002)
        mail = CharacterMail.objects.create(
            character=self.character_1001,
            mail_id=1,
            sender=sender,
            subject="Mail 1",
            timestamp=parse_datetime("2015-09-05T16:07:00Z"),
            is_read=False,  # to be updated
        )
        recipient_1, _ = MailEntity.objects.update_or_create_from_eve_entity_id(id=1001)
        recipient_2 = MailEntity.objects.create(
            id=9001, category=MailEntity.Category.MAILING_LIST, name="Dummy 2"
        )
        mail.recipients.set([recipient_1, recipient_2])

        self.character_1001.update_mailing_lists()
        self.character_1001.update_mail_labels()
        label = self.character_1001.mail_labels.get(label_id=17)
        mail.labels.add(label)  # to be updated

        self.character_1001.update_mail_headers()
        self.assertSetEqual(
            set(self.character_1001.mails.values_list("mail_id", flat=True)),
            {1, 2, 3},
        )

        obj = self.character_1001.mails.get(mail_id=1)
        self.assertEqual(obj.sender_id, 1002)
        self.assertTrue(obj.is_read)
        self.assertEqual(obj.subject, "Mail 1")
        self.assertEqual(obj.timestamp, parse_datetime("2015-09-05T16:07:00Z"))
        self.assertFalse(obj.body)
        self.assertTrue(obj.recipients.filter(id=1001).exists())
        self.assertTrue(obj.recipients.filter(id=9001).exists())
        self.assertSetEqual(set(obj.labels.values_list("label_id", flat=True)), {3})

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    @patch(MANAGERS_PATH + ".general.fetch_esi_status")
    @patch(MANAGERS_PATH + ".sections.EveEntity.objects.get_or_create_esi")
    def test_update_mail_headers_3(
        self, mock_eve_entity, mock_fetch_esi_status, mock_esi
    ):
        """when ESI data is unchanged, then skip update"""
        mock_esi.client = esi_client_stub
        mock_eve_entity.side_effect = self.stub_eve_entity_get_or_create_esi
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)

        self.character_1001.update_mailing_lists()
        self.character_1001.update_mail_labels()
        self.character_1001.update_mail_headers()
        obj = self.character_1001.mails.get(mail_id=1)
        obj.is_read = False
        obj.save()

        self.character_1001.update_mail_headers()

        obj = self.character_1001.mails.get(mail_id=1)
        self.assertFalse(obj.is_read)

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    @patch(MANAGERS_PATH + ".general.fetch_esi_status")
    @patch(MANAGERS_PATH + ".sections.EveEntity.objects.get_or_create_esi")
    def test_update_mail_headers_4(
        self, mock_eve_entity, mock_fetch_esi_status, mock_esi
    ):
        """when ESI data is unchanged and update forced, then do update"""
        mock_esi.client = esi_client_stub
        mock_eve_entity.side_effect = self.stub_eve_entity_get_or_create_esi
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)

        self.character_1001.update_mailing_lists()
        self.character_1001.update_mail_labels()
        self.character_1001.update_mail_headers()
        obj = self.character_1001.mails.get(mail_id=1)
        obj.is_read = False
        obj.save()

        self.character_1001.update_mail_headers(force_update=True)

        obj = self.character_1001.mails.get(mail_id=1)
        self.assertTrue(obj.is_read)

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", 15)
    @patch(MANAGERS_PATH + ".general.fetch_esi_status")
    @patch(MANAGERS_PATH + ".sections.EveEntity.objects.get_or_create_esi")
    def test_update_mail_headers_6(
        self, mock_eve_entity, mock_fetch_esi_status, mock_esi
    ):
        """when data retention limit is set, then only fetch mails within that limit"""
        mock_esi.client = esi_client_stub
        mock_eve_entity.side_effect = self.stub_eve_entity_get_or_create_esi
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)

        with patch(MODELS_PATH + ".character.now") as mock_now:
            mock_now.return_value = dt.datetime(2015, 9, 20, 20, 5, tzinfo=utc)
            self.character_1001.update_mailing_lists()
            self.character_1001.update_mail_labels()
            self.character_1001.update_mail_headers()

        self.assertSetEqual(
            set(self.character_1001.mails.values_list("mail_id", flat=True)),
            {2, 3},
        )

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", 15)
    @patch(MANAGERS_PATH + ".general.fetch_esi_status")
    @patch(MANAGERS_PATH + ".sections.EveEntity.objects.get_or_create_esi")
    def test_update_mail_headers_7(
        self, mock_eve_entity, mock_fetch_esi_status, mock_esi
    ):
        """when data retention limit is set, then remove old data beyond that limit"""
        mock_esi.client = esi_client_stub
        mock_eve_entity.side_effect = self.stub_eve_entity_get_or_create_esi
        mock_fetch_esi_status.return_value = EsiStatus(True, 99, 60)
        sender, _ = MailEntity.objects.update_or_create_from_eve_entity_id(id=1002)
        CharacterMail.objects.create(
            character=self.character_1001,
            mail_id=99,
            sender=sender,
            subject="Mail Old",
            timestamp=parse_datetime("2015-09-02T14:02:00Z"),
            is_read=False,
        )

        with patch(MODELS_PATH + ".character.now") as mock_now:
            mock_now.return_value = dt.datetime(2015, 9, 20, 20, 5, tzinfo=utc)
            self.character_1001.update_mailing_lists()
            self.character_1001.update_mail_labels()
            self.character_1001.update_mail_headers()

        self.assertSetEqual(
            set(self.character_1001.mails.values_list("mail_id", flat=True)),
            {2, 3},
        )

    def test_should_update_existing_mail_body(self, mock_esi):
        # given
        mock_esi.client = esi_client_stub
        sender, _ = MailEntity.objects.update_or_create_from_eve_entity_id(id=1002)
        mail = CharacterMail.objects.create(
            character=self.character_1001,
            mail_id=1,
            sender=sender,
            subject="Mail 1",
            body="Update me",
            is_read=False,
            timestamp=parse_datetime("2015-09-30T16:07:00Z"),
        )
        recipient_1001, _ = MailEntity.objects.update_or_create_from_eve_entity_id(
            id=1001
        )
        recipient_9001 = MailEntity.objects.create(
            id=9001, category=MailEntity.Category.MAILING_LIST, name="Dummy 2"
        )
        mail.recipients.add(recipient_1001, recipient_9001)
        # when
        self.character_1001.update_mail_body(mail)
        # then
        obj = self.character_1001.mails.get(mail_id=1)
        self.assertEqual(obj.body, "blah blah blah")

    @patch(MODELS_PATH + ".character.eve_xml_to_html")
    def test_should_update_mail_body_from_scratch(self, mock_eve_xml_to_html, mock_esi):
        # given
        mock_esi.client = esi_client_stub
        mock_eve_xml_to_html.side_effect = lambda x: eve_xml_to_html(x)
        sender, _ = MailEntity.objects.update_or_create_from_eve_entity_id(id=1002)
        mail = CharacterMail.objects.create(
            character=self.character_1001,
            mail_id=2,
            sender=sender,
            subject="Mail 1",
            is_read=False,
            timestamp=parse_datetime("2015-09-30T16:07:00Z"),
        )
        recipient_1, _ = MailEntity.objects.update_or_create_from_eve_entity_id(id=1001)
        mail.recipients.add(recipient_1)
        # when
        self.character_1001.update_mail_body(mail)
        # then
        obj = self.character_1001.mails.get(mail_id=2)
        self.assertTrue(obj.body)
        self.assertTrue(mock_eve_xml_to_html.called)

    def test_should_delete_mail_header_when_fetching_body_returns_404(self, mock_esi):
        # given
        mock_esi.client.Mail.get_characters_character_id_mail_mail_id.side_effect = (
            HTTPNotFound(response=BravadoResponseStub(404, "Test"))
        )
        sender, _ = MailEntity.objects.update_or_create_from_eve_entity_id(id=1002)
        mail = CharacterMail.objects.create(
            character=self.character_1001,
            mail_id=1,
            sender=sender,
            subject="Mail 1",
            is_read=False,
            timestamp=parse_datetime("2015-09-30T16:07:00Z"),
        )
        recipient_1001, _ = MailEntity.objects.update_or_create_from_eve_entity_id(
            id=1001
        )
        recipient_9001 = MailEntity.objects.create(
            id=9001, category=MailEntity.Category.MAILING_LIST, name="Dummy 2"
        )
        mail.recipients.add(recipient_1001, recipient_9001)
        # when
        self.character_1001.update_mail_body(mail)
        # then
        self.assertFalse(self.character_1001.mails.filter(mail_id=1).exists())


@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateLoyalty(CharacterUpdateTestDataMixin, NoSocketsTestCase):
    def test_create(self, mock_esi):
        """can create from scratch"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_loyalty()
        self.assertEqual(self.character_1001.loyalty_entries.count(), 1)

        obj = self.character_1001.loyalty_entries.get(corporation_id=2002)
        self.assertEqual(obj.loyalty_points, 100)

    def test_update(self, mock_esi):
        """can update existing loyalty"""
        mock_esi.client = esi_client_stub
        self.character_1001.loyalty_entries.create(
            corporation=self.corporation_2001, loyalty_points=200
        )

        self.character_1001.update_loyalty()
        self.assertEqual(self.character_1001.loyalty_entries.count(), 1)

        obj = self.character_1001.loyalty_entries.get(corporation=self.corporation_2002)
        self.assertEqual(obj.loyalty_points, 100)

    def test_skip_update_1(self, mock_esi):
        """when data from ESI has not changed, then skip update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_loyalty()
        obj = self.character_1001.loyalty_entries.get(corporation=self.corporation_2002)
        obj.loyalty_points = 200
        obj.save()
        self.character_1001.update_loyalty()

        obj = self.character_1001.loyalty_entries.get(corporation=self.corporation_2002)
        self.assertEqual(obj.loyalty_points, 200)

    def test_skip_update_2(self, mock_esi):
        """when data from ESI has not changed and update is forced, then do update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_loyalty()
        obj = self.character_1001.loyalty_entries.get(corporation=self.corporation_2002)
        obj.loyalty_points = 200
        obj.save()

        self.character_1001.update_loyalty(force_update=True)

        obj = self.character_1001.loyalty_entries.get(corporation=self.corporation_2002)
        self.assertEqual(obj.loyalty_points, 100)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateLocation(CharacterUpdateTestDataMixin, NoSocketsTestCase):
    def test_update_location_1(self, mock_esi):
        mock_esi.client = esi_client_stub

        self.character_1001.update_location()
        self.assertEqual(self.character_1001.location.eve_solar_system, self.jita)
        self.assertEqual(self.character_1001.location.location, self.jita_44)

    def test_update_location_2(self, mock_esi):
        mock_esi.client = esi_client_stub

        self.character_1002.update_location()
        self.assertEqual(self.character_1002.location.eve_solar_system, self.amamake)
        self.assertEqual(self.character_1002.location.location, self.structure_1)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateOnlineStatus(CharacterUpdateTestDataMixin, NoSocketsTestCase):
    def test_update_online_status(self, mock_esi):
        mock_esi.client = esi_client_stub

        self.character_1001.update_online_status()
        self.assertEqual(
            self.character_1001.online_status.last_login,
            parse_datetime("2017-01-02T03:04:05Z"),
        )
        self.assertEqual(
            self.character_1001.online_status.last_logout,
            parse_datetime("2017-01-02T04:05:06Z"),
        )
        self.assertEqual(self.character_1001.online_status.logins, 9001)


@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateShip(CharacterUpdateTestDataMixin, NoSocketsTestCase):
    def test_should_update_all_fields(self, mock_esi):
        # given
        mock_esi.client = esi_client_stub
        # when
        self.character_1001.update_ship()
        # then
        self.assertEqual(self.character_1001.ship.eve_type, EveType.objects.get(id=603))
        self.assertEqual(self.character_1001.ship.name, "Shooter Boy")


@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateSkills(CharacterUpdateTestDataMixin, NoSocketsTestCase):
    def test_update_skills_1(self, mock_esi):
        """can create new skills"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_skills()
        self.assertEqual(self.character_1001.skillpoints.total, 30_000)
        self.assertEqual(self.character_1001.skillpoints.unallocated, 1_000)

        self.assertSetEqual(
            set(self.character_1001.skills.values_list("eve_type_id", flat=True)),
            {24311, 24312},
        )

        skill = self.character_1001.skills.get(eve_type_id=24311)
        self.assertEqual(skill.active_skill_level, 3)
        self.assertEqual(skill.skillpoints_in_skill, 20_000)
        self.assertEqual(skill.trained_skill_level, 4)

        skill = self.character_1001.skills.get(eve_type_id=24312)
        self.assertEqual(skill.active_skill_level, 1)
        self.assertEqual(skill.skillpoints_in_skill, 10_000)
        self.assertEqual(skill.trained_skill_level, 1)

    def test_update_skills_2(self, mock_esi):
        """can update existing skills"""
        mock_esi.client = esi_client_stub

        CharacterSkill.objects.create(
            character=self.character_1001,
            eve_type=EveType.objects.get(id=24311),
            active_skill_level=1,
            skillpoints_in_skill=1,
            trained_skill_level=1,
        )

        self.character_1001.update_skills()

        self.assertEqual(self.character_1001.skills.count(), 2)
        skill = self.character_1001.skills.get(eve_type_id=24311)
        self.assertEqual(skill.active_skill_level, 3)
        self.assertEqual(skill.skillpoints_in_skill, 20_000)
        self.assertEqual(skill.trained_skill_level, 4)

    def test_update_skills_3(self, mock_esi):
        """can delete obsolete skills"""
        mock_esi.client = esi_client_stub

        CharacterSkill.objects.create(
            character=self.character_1001,
            eve_type=EveType.objects.get(id=20185),
            active_skill_level=1,
            skillpoints_in_skill=1,
            trained_skill_level=1,
        )

        self.character_1001.update_skills()

        self.assertSetEqual(
            set(self.character_1001.skills.values_list("eve_type_id", flat=True)),
            {24311, 24312},
        )

    def test_update_skills_4(self, mock_esi):
        """when ESI info has not changed, then do not update local data"""
        mock_esi.client = esi_client_stub

        self.character_1001.reset_update_section(Character.UpdateSection.SKILLS)
        self.character_1001.update_skills()
        skill = self.character_1001.skills.get(eve_type_id=24311)
        skill.active_skill_level = 4
        skill.save()
        self.character_1001.update_skills()
        skill.refresh_from_db()
        self.assertEqual(skill.active_skill_level, 4)

    def test_update_skills_5(self, mock_esi):
        """when ESI info has not changed and update forced, then update local data"""
        mock_esi.client = esi_client_stub

        self.character_1001.reset_update_section(Character.UpdateSection.SKILLS)
        self.character_1001.update_skills()
        skill = self.character_1001.skills.get(eve_type_id=24311)
        skill.active_skill_level = 4
        skill.save()

        self.character_1001.update_skills(force_update=True)

        skill = self.character_1001.skills.get(eve_type_id=24311)
        self.assertEqual(skill.active_skill_level, 3)


@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateSkillQueue(CharacterUpdateTestDataMixin, NoSocketsTestCase):
    def test_create(self, mock_esi):
        """can create skill queue from scratch"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_skill_queue()
        self.assertEqual(self.character_1001.skillqueue.count(), 3)

        entry = self.character_1001.skillqueue.get(queue_position=0)
        self.assertEqual(entry.eve_type, EveType.objects.get(id=24311))
        self.assertEqual(entry.finish_date, parse_datetime("2016-06-29T10:47:00Z"))
        self.assertEqual(entry.finished_level, 3)
        self.assertEqual(entry.start_date, parse_datetime("2016-06-29T10:46:00Z"))

        entry = self.character_1001.skillqueue.get(queue_position=1)
        self.assertEqual(entry.eve_type, EveType.objects.get(id=24312))
        self.assertEqual(entry.finish_date, parse_datetime("2016-07-15T10:47:00Z"))
        self.assertEqual(entry.finished_level, 4)
        self.assertEqual(entry.level_end_sp, 1000)
        self.assertEqual(entry.level_start_sp, 100)
        self.assertEqual(entry.start_date, parse_datetime("2016-06-29T10:47:00Z"))
        self.assertEqual(entry.training_start_sp, 50)

        entry = self.character_1001.skillqueue.get(queue_position=2)
        self.assertEqual(entry.eve_type, EveType.objects.get(id=24312))
        self.assertEqual(entry.finished_level, 5)

    def test_update_1(self, mock_esi):
        """can update existing skill queue"""
        mock_esi.client = esi_client_stub
        self.character_1001.skillqueue.create(
            queue_position=0,
            eve_type=EveType.objects.get(id=24311),
            finish_date=now() + dt.timedelta(days=1),
            finished_level=4,
            start_date=now() - dt.timedelta(days=1),
        )

        self.character_1001.update_skill_queue()
        self.assertEqual(self.character_1001.skillqueue.count(), 3)

        entry = self.character_1001.skillqueue.get(queue_position=0)
        self.assertEqual(entry.eve_type, EveType.objects.get(id=24311))
        self.assertEqual(entry.finish_date, parse_datetime("2016-06-29T10:47:00Z"))
        self.assertEqual(entry.finished_level, 3)
        self.assertEqual(entry.start_date, parse_datetime("2016-06-29T10:46:00Z"))

    def test_skip_update_1(self, mock_esi):
        """when ESI data has not changed, then skip update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_skill_queue()
        entry = self.character_1001.skillqueue.get(queue_position=0)
        entry.finished_level = 4
        entry.save()

        self.character_1001.update_skill_queue()
        entry = self.character_1001.skillqueue.get(queue_position=0)
        self.assertEqual(entry.finished_level, 4)

    def test_skip_update_2(self, mock_esi):
        """when ESI data has not changed and update is forced, then do update"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_skill_queue()
        entry = self.character_1001.skillqueue.get(queue_position=0)
        entry.finished_level = 4
        entry.save()

        self.character_1001.update_skill_queue(force_update=True)
        entry = self.character_1001.skillqueue.get(queue_position=0)
        self.assertEqual(entry.finished_level, 3)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateWalletJournal(CharacterUpdateTestDataMixin, NoSocketsTestCase):
    def test_update_wallet_balance(self, mock_esi):
        mock_esi.client = esi_client_stub

        self.character_1001.update_wallet_balance()
        self.assertEqual(self.character_1001.wallet_balance.total, 123456789)

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    def test_update_wallet_journal_1(self, mock_esi):
        """can create wallet journal entry from scratch"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_wallet_journal()

        self.assertSetEqual(
            set(self.character_1001.wallet_journal.values_list("entry_id", flat=True)),
            {89, 91},
        )
        obj = self.character_1001.wallet_journal.get(entry_id=89)
        self.assertEqual(obj.amount, -100_000)
        self.assertEqual(float(obj.balance), 500_000.43)
        self.assertEqual(obj.context_id, 4)
        self.assertEqual(obj.context_id_type, obj.CONTEXT_ID_TYPE_CONTRACT_ID)
        self.assertEqual(obj.date, parse_datetime("2018-02-23T14:31:32Z"))
        self.assertEqual(obj.description, "Contract Deposit")
        self.assertEqual(obj.first_party.id, 2001)
        self.assertEqual(obj.reason, "just for fun")
        self.assertEqual(obj.ref_type, "contract_deposit")
        self.assertEqual(obj.second_party.id, 2002)

        obj = self.character_1001.wallet_journal.get(entry_id=91)
        self.assertEqual(
            obj.ref_type, "agent_mission_time_bonus_reward_corporation_tax"
        )

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    def test_update_wallet_journal_2(self, mock_esi):
        """can add entry to existing wallet journal"""
        mock_esi.client = esi_client_stub
        CharacterWalletJournalEntry.objects.create(
            character=self.character_1001,
            entry_id=1,
            amount=1_000_000,
            balance=10_000_000,
            context_id_type=CharacterWalletJournalEntry.CONTEXT_ID_TYPE_UNDEFINED,
            date=now(),
            description="dummy",
            first_party=EveEntity.objects.get(id=1001),
            second_party=EveEntity.objects.get(id=1002),
        )

        self.character_1001.update_wallet_journal()

        self.assertSetEqual(
            set(self.character_1001.wallet_journal.values_list("entry_id", flat=True)),
            {1, 89, 91},
        )

        obj = self.character_1001.wallet_journal.get(entry_id=89)
        self.assertEqual(obj.amount, -100_000)
        self.assertEqual(float(obj.balance), 500_000.43)
        self.assertEqual(obj.context_id, 4)
        self.assertEqual(obj.context_id_type, obj.CONTEXT_ID_TYPE_CONTRACT_ID)
        self.assertEqual(obj.date, parse_datetime("2018-02-23T14:31:32Z"))
        self.assertEqual(obj.description, "Contract Deposit")
        self.assertEqual(obj.first_party.id, 2001)
        self.assertEqual(obj.ref_type, "contract_deposit")
        self.assertEqual(obj.second_party.id, 2002)

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None)
    def test_update_wallet_journal_3(self, mock_esi):
        """does not update existing entries"""
        mock_esi.client = esi_client_stub
        CharacterWalletJournalEntry.objects.create(
            character=self.character_1001,
            entry_id=89,
            amount=1_000_000,
            balance=10_000_000,
            context_id_type=CharacterWalletJournalEntry.CONTEXT_ID_TYPE_UNDEFINED,
            date=now(),
            description="dummy",
            first_party=EveEntity.objects.get(id=1001),
            second_party=EveEntity.objects.get(id=1002),
        )

        self.character_1001.update_wallet_journal()

        self.assertSetEqual(
            set(self.character_1001.wallet_journal.values_list("entry_id", flat=True)),
            {89, 91},
        )
        obj = self.character_1001.wallet_journal.get(entry_id=89)
        self.assertEqual(obj.amount, 1_000_000)
        self.assertEqual(float(obj.balance), 10_000_000)
        self.assertEqual(
            obj.context_id_type, CharacterWalletJournalEntry.CONTEXT_ID_TYPE_UNDEFINED
        )
        self.assertEqual(obj.description, "dummy")
        self.assertEqual(obj.first_party.id, 1001)
        self.assertEqual(obj.second_party.id, 1002)

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", 10)
    def test_update_wallet_journal_4(self, mock_esi):
        """When new wallet entry is older than retention limit, then do not store it"""
        mock_esi.client = esi_client_stub

        with patch(MODELS_PATH + ".character.now") as mock_now:
            mock_now.return_value = dt.datetime(2018, 3, 11, 20, 5, tzinfo=utc)
            self.character_1001.update_wallet_journal()

        self.assertSetEqual(
            set(self.character_1001.wallet_journal.values_list("entry_id", flat=True)),
            {91},
        )

    @patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", 20)
    def test_update_wallet_journal_5(self, mock_esi):
        """When wallet existing entry is older than retention limit, then delete it"""
        mock_esi.client = esi_client_stub
        CharacterWalletJournalEntry.objects.create(
            character=self.character_1001,
            entry_id=55,
            amount=1_000_000,
            balance=10_000_000,
            context_id_type=CharacterWalletJournalEntry.CONTEXT_ID_TYPE_UNDEFINED,
            date=dt.datetime(2018, 2, 11, 20, 5, tzinfo=utc),
            description="dummy",
            first_party=EveEntity.objects.get(id=1001),
            second_party=EveEntity.objects.get(id=1002),
        )

        with patch(MODELS_PATH + ".character.now") as mock_now:
            mock_now.return_value = dt.datetime(2018, 3, 11, 20, 5, tzinfo=utc)
            self.character_1001.update_wallet_journal()

        self.assertSetEqual(
            set(self.character_1001.wallet_journal.values_list("entry_id", flat=True)),
            {89, 91},
        )


@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateWalletTransaction(
    CharacterUpdateTestDataMixin, NoSocketsTestCase
):
    def test_should_add_wallet_transactions_from_scratch(self, mock_esi):
        # given
        mock_esi.client = esi_client_stub
        # when
        with patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None):
            self.character_1001.update_wallet_transactions()
        # then
        self.assertSetEqual(
            set(
                self.character_1001.wallet_transactions.values_list(
                    "transaction_id", flat=True
                )
            ),
            {42},
        )
        obj = self.character_1001.wallet_transactions.get(transaction_id=42)
        self.assertEqual(obj.client, EveEntity.objects.get(id=1003))
        self.assertEqual(obj.date, parse_datetime("2016-10-24T09:00:00Z"))
        self.assertTrue(obj.is_buy)
        self.assertTrue(obj.is_personal)
        self.assertIsNone(obj.journal_ref)
        self.assertEqual(obj.location, Location.objects.get(id=60003760))
        self.assertEqual(obj.quantity, 3)
        self.assertEqual(obj.eve_type, EveType.objects.get(id=603))
        self.assertEqual(float(obj.unit_price), 450000.99)

    def test_should_add_wallet_transactions_from_scratch_with_journal_ref(
        self, mock_esi
    ):
        # given
        mock_esi.client = esi_client_stub
        journal_entry = CharacterWalletJournalEntry.objects.create(
            character=self.character_1001,
            entry_id=67890,
            amount=450000.99,
            balance=10_000_000,
            context_id_type=CharacterWalletJournalEntry.CONTEXT_ID_TYPE_UNDEFINED,
            date=parse_datetime("2016-10-24T09:00:00Z"),
            description="dummy",
            first_party=EveEntity.objects.get(id=1001),
            second_party=EveEntity.objects.get(id=1003),
        )
        # when
        with patch(MODELS_PATH + ".character.MEMBERAUDIT_DATA_RETENTION_LIMIT", None):
            self.character_1001.update_wallet_transactions()
        # then
        self.assertSetEqual(
            set(
                self.character_1001.wallet_transactions.values_list(
                    "transaction_id", flat=True
                )
            ),
            {42},
        )
        obj = self.character_1001.wallet_transactions.get(transaction_id=42)
        self.assertEqual(obj.journal_ref, journal_entry)


# class TestCharacterMailingList(CharacterUpdateTestDataMixin, NoSocketsTestCase):
#     def test_name_plus_1(self):
#         """when mailing list has name then return it's name"""
#         mailing_list = CharacterMailingList(
#             self.character_1001, list_id=99, name="Avengers Talk"
#         )
#         self.assertEqual(mailing_list.name_plus, "Avengers Talk")

#     def test_name_plus_2(self):
#         """when mailing list has no name then return a generic name"""
#         mailing_list = CharacterMailingList(self.character_1001, list_id=99)
#         self.assertEqual(mailing_list.name_plus, "Mailing list #99")


@patch(MODELS_PATH + ".character.esi")
class TestCharacterUpdateAttributes(CharacterUpdateTestDataMixin, NoSocketsTestCase):
    def test_create(self, mock_esi):
        """can load attributes from test data"""
        mock_esi.client = esi_client_stub

        self.character_1001.update_attributes()
        self.assertEqual(
            self.character_1001.attributes.accrued_remap_cooldown_date,
            parse_datetime("2016-10-24T09:00:00Z"),
        )

        self.assertEqual(
            self.character_1001.attributes.last_remap_date,
            parse_datetime("2016-10-24T09:00:00Z"),
        )

        self.assertEqual(self.character_1001.attributes.charisma, 16)
        self.assertEqual(self.character_1001.attributes.intelligence, 17)
        self.assertEqual(self.character_1001.attributes.memory, 18)
        self.assertEqual(self.character_1001.attributes.perception, 19)
        self.assertEqual(self.character_1001.attributes.willpower, 20)

    def test_update(self, mock_esi):
        """can create attributes from scratch"""
        mock_esi.client = esi_client_stub

        CharacterAttributes.objects.create(
            character=self.character_1001,
            accrued_remap_cooldown_date="2020-10-24T09:00:00Z",
            last_remap_date="2020-10-24T09:00:00Z",
            bonus_remaps=4,
            charisma=102,
            intelligence=103,
            memory=104,
            perception=105,
            willpower=106,
        )

        self.character_1001.update_attributes()
        self.character_1001.attributes.refresh_from_db()

        self.assertEqual(
            self.character_1001.attributes.accrued_remap_cooldown_date,
            parse_datetime("2016-10-24T09:00:00Z"),
        )

        self.assertEqual(
            self.character_1001.attributes.last_remap_date,
            parse_datetime("2016-10-24T09:00:00Z"),
        )

        self.assertEqual(self.character_1001.attributes.charisma, 16)
        self.assertEqual(self.character_1001.attributes.intelligence, 17)
        self.assertEqual(self.character_1001.attributes.memory, 18)
        self.assertEqual(self.character_1001.attributes.perception, 19)
        self.assertEqual(self.character_1001.attributes.willpower, 20)
