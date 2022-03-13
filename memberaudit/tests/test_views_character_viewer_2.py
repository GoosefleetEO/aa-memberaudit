import datetime as dt
from unittest.mock import patch

import pytz

from django.test import RequestFactory, TestCase
from django.urls import reverse
from eveuniverse.models import EveEntity, EveMarketPrice

from app_utils.testing import (
    generate_invalid_pk,
    json_response_to_dict,
    json_response_to_python,
    response_text,
)

from ..models import CharacterContract, CharacterContractItem, CharacterMail
from ..views.character_viewer import (
    character_contract_details,
    character_contract_items_included_data,
    character_contract_items_requested_data,
    character_contracts_data,
    character_mail,
    character_mail_headers_by_label_data,
    character_mail_headers_by_list_data,
)
from .testdata.factories import (
    create_character_mail,
    create_character_mail_label,
    create_mail_entity_from_eve_entity,
    create_mailing_list,
)
from .testdata.load_entities import load_entities
from .testdata.load_eveuniverse import load_eveuniverse
from .utils import LoadTestDataMixin, create_memberaudit_character

MODULE_PATH = "memberaudit.views.character_viewer"


class TestCharacterContracts(LoadTestDataMixin, TestCase):
    @patch(MODULE_PATH + ".now")
    def test_character_contracts_data_1(self, mock_now):
        """items exchange single item"""
        date_issued = dt.datetime(2020, 10, 8, 16, 45, tzinfo=pytz.utc)
        date_now = date_issued + dt.timedelta(days=1)
        date_expired = date_now + dt.timedelta(days=2, hours=3)
        mock_now.return_value = date_now
        contract = CharacterContract.objects.create(
            character=self.character,
            contract_id=42,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_ITEM_EXCHANGE,
            assignee=EveEntity.objects.get(id=1002),
            date_issued=date_issued,
            date_expired=date_expired,
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_IN_PROGRESS,
            start_location=self.jita_44,
            end_location=self.jita_44,
            title="Dummy info",
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=1,
            is_included=True,
            is_singleton=False,
            quantity=1,
            eve_type=self.item_type_1,
        )

        # main view
        request = self.factory.get(
            reverse("memberaudit:character_contracts_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_contracts_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(row["contract_id"], 42)
        self.assertEqual(row["summary"], "High-grade Snake Alpha")
        self.assertEqual(row["type"], "Item Exchange")
        self.assertEqual(row["from"], "Bruce Wayne")
        self.assertEqual(row["to"], "Clark Kent")
        self.assertEqual(row["status"], "in progress")
        self.assertEqual(row["date_issued"], date_issued.isoformat())
        self.assertEqual(row["time_left"], "2\xa0days, 3\xa0hours")
        self.assertEqual(row["info"], "Dummy info")

        # details view
        request = self.factory.get(
            reverse(
                "memberaudit:character_contract_details",
                args=[self.character.pk, contract.pk],
            )
        )
        request.user = self.user
        response = character_contract_details(request, self.character.pk, contract.pk)
        self.assertEqual(response.status_code, 200)

    @patch(MODULE_PATH + ".now")
    def test_character_contracts_data_2(self, mock_now):
        """items exchange multiple item"""
        date_issued = dt.datetime(2020, 10, 8, 16, 45, tzinfo=pytz.utc)
        date_now = date_issued + dt.timedelta(days=1)
        date_expired = date_now + dt.timedelta(days=2, hours=3)
        mock_now.return_value = date_now
        contract = CharacterContract.objects.create(
            character=self.character,
            availability=CharacterContract.AVAILABILITY_PUBLIC,
            contract_id=42,
            contract_type=CharacterContract.TYPE_ITEM_EXCHANGE,
            assignee=EveEntity.objects.get(id=1002),
            date_issued=date_issued,
            date_expired=date_expired,
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_IN_PROGRESS,
            title="Dummy info",
            start_location=self.jita_44,
            end_location=self.jita_44,
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=1,
            is_included=True,
            is_singleton=False,
            quantity=1,
            eve_type=self.item_type_1,
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=2,
            is_included=True,
            is_singleton=False,
            quantity=1,
            eve_type=self.item_type_2,
        )
        request = self.factory.get(
            reverse("memberaudit:character_contracts_data", args=[self.character.pk])
        )

        # main view
        request.user = self.user
        response = character_contracts_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(row["contract_id"], 42)
        self.assertEqual(row["summary"], "[Multiple Items]")
        self.assertEqual(row["type"], "Item Exchange")

        # details view
        request = self.factory.get(
            reverse(
                "memberaudit:character_contract_details",
                args=[self.character.pk, contract.pk],
            )
        )
        request.user = self.user
        response = character_contract_details(request, self.character.pk, contract.pk)
        self.assertEqual(response.status_code, 200)

    @patch(MODULE_PATH + ".now")
    def test_character_contracts_data_3(self, mock_now):
        """courier contract"""
        date_issued = dt.datetime(2020, 10, 8, 16, 45, tzinfo=pytz.utc)
        date_now = date_issued + dt.timedelta(days=1)
        date_expired = date_now + dt.timedelta(days=2, hours=3)
        mock_now.return_value = date_now
        contract = CharacterContract.objects.create(
            character=self.character,
            contract_id=42,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_COURIER,
            assignee=EveEntity.objects.get(id=1002),
            date_issued=date_issued,
            date_expired=date_expired,
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_IN_PROGRESS,
            title="Dummy info",
            start_location=self.jita_44,
            end_location=self.structure_1,
            volume=10,
            days_to_complete=3,
            reward=10000000,
            collateral=500000000,
        )

        # main view
        request = self.factory.get(
            reverse("memberaudit:character_contracts_data", args=[self.character.pk])
        )
        request.user = self.user
        response = character_contracts_data(request, self.character.pk)
        self.assertEqual(response.status_code, 200)
        data = json_response_to_python(response)
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(row["contract_id"], 42)
        self.assertEqual(row["summary"], "Jita >> Amamake (10 m3)")
        self.assertEqual(row["type"], "Courier")

        # details view
        request = self.factory.get(
            reverse(
                "memberaudit:character_contract_details",
                args=[self.character.pk, contract.pk],
            )
        )
        request.user = self.user
        response = character_contract_details(request, self.character.pk, contract.pk)
        self.assertEqual(response.status_code, 200)

    def test_character_contract_details_error(self):
        contract_pk = generate_invalid_pk(CharacterContract)
        request = self.factory.get(
            reverse(
                "memberaudit:character_contract_details",
                args=[self.character.pk, contract_pk],
            )
        )
        request.user = self.user
        response = character_contract_details(request, self.character.pk, contract_pk)
        self.assertEqual(response.status_code, 200)
        self.assertIn("not found for character", response_text(response))

    @patch(MODULE_PATH + ".now")
    def test_items_included_data_normal(self, mock_now):
        """items exchange single item"""
        date_issued = dt.datetime(2020, 10, 8, 16, 45, tzinfo=pytz.utc)
        date_now = date_issued + dt.timedelta(days=1)
        date_expired = date_now + dt.timedelta(days=2, hours=3)
        mock_now.return_value = date_now
        contract = CharacterContract.objects.create(
            character=self.character,
            contract_id=42,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_ITEM_EXCHANGE,
            assignee=EveEntity.objects.get(id=1002),
            date_issued=date_issued,
            date_expired=date_expired,
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_IN_PROGRESS,
            start_location=self.jita_44,
            end_location=self.jita_44,
            title="Dummy info",
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=1,
            is_included=True,
            is_singleton=False,
            quantity=3,
            eve_type=self.item_type_1,
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=2,
            is_included=False,
            is_singleton=False,
            quantity=3,
            eve_type=self.item_type_2,
        )
        EveMarketPrice.objects.create(eve_type=self.item_type_1, average_price=5000000)
        request = self.factory.get(
            reverse(
                "memberaudit:character_contract_items_included_data",
                args=[self.character.pk, contract.pk],
            )
        )
        request.user = self.user
        response = character_contract_items_included_data(
            request, self.character.pk, contract.pk
        )
        self.assertEqual(response.status_code, 200)
        data = json_response_to_dict(response)

        self.assertSetEqual(set(data.keys()), {1})
        obj = data[1]
        self.assertEqual(obj["name"]["sort"], "High-grade Snake Alpha")
        self.assertEqual(obj["quantity"], 3)
        self.assertEqual(obj["group"], "Cyberimplant")
        self.assertEqual(obj["category"], "Implant")
        self.assertEqual(obj["price"], 5000000)
        self.assertEqual(obj["total"], 15000000)
        self.assertFalse(obj["is_blueprint_copy"])

    @patch(MODULE_PATH + ".now")
    def test_items_included_data_bpo(self, mock_now):
        """items exchange single item, which is an BPO"""
        date_issued = dt.datetime(2020, 10, 8, 16, 45, tzinfo=pytz.utc)
        date_now = date_issued + dt.timedelta(days=1)
        date_expired = date_now + dt.timedelta(days=2, hours=3)
        mock_now.return_value = date_now
        contract = CharacterContract.objects.create(
            character=self.character,
            contract_id=42,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_ITEM_EXCHANGE,
            assignee=EveEntity.objects.get(id=1002),
            date_issued=date_issued,
            date_expired=date_expired,
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_IN_PROGRESS,
            start_location=self.jita_44,
            end_location=self.jita_44,
            title="Dummy info",
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=1,
            is_included=True,
            is_singleton=True,
            quantity=1,
            raw_quantity=-2,
            eve_type=self.item_type_1,
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=2,
            is_included=True,
            is_singleton=False,
            quantity=3,
            eve_type=self.item_type_2,
        )
        EveMarketPrice.objects.create(eve_type=self.item_type_1, average_price=5000000)
        request = self.factory.get(
            reverse(
                "memberaudit:character_contract_items_included_data",
                args=[self.character.pk, contract.pk],
            )
        )
        request.user = self.user
        response = character_contract_items_included_data(
            request, self.character.pk, contract.pk
        )
        self.assertEqual(response.status_code, 200)
        data = json_response_to_dict(response)

        self.assertSetEqual(set(data.keys()), {1, 2})
        obj = data[1]
        self.assertEqual(obj["name"]["sort"], "High-grade Snake Alpha [BPC]")
        self.assertEqual(obj["quantity"], "")
        self.assertEqual(obj["group"], "Cyberimplant")
        self.assertEqual(obj["category"], "Implant")
        self.assertIsNone(obj["price"])
        self.assertIsNone(obj["total"])
        self.assertTrue(obj["is_blueprint_copy"])

    @patch(MODULE_PATH + ".now")
    def test_items_requested_data_normal(self, mock_now):
        """items exchange single item"""
        date_issued = dt.datetime(2020, 10, 8, 16, 45, tzinfo=pytz.utc)
        date_now = date_issued + dt.timedelta(days=1)
        date_expired = date_now + dt.timedelta(days=2, hours=3)
        mock_now.return_value = date_now
        contract = CharacterContract.objects.create(
            character=self.character,
            contract_id=42,
            availability=CharacterContract.AVAILABILITY_PERSONAL,
            contract_type=CharacterContract.TYPE_ITEM_EXCHANGE,
            assignee=EveEntity.objects.get(id=1002),
            date_issued=date_issued,
            date_expired=date_expired,
            for_corporation=False,
            issuer=EveEntity.objects.get(id=1001),
            issuer_corporation=EveEntity.objects.get(id=2001),
            status=CharacterContract.STATUS_IN_PROGRESS,
            start_location=self.jita_44,
            end_location=self.jita_44,
            title="Dummy info",
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=1,
            is_included=False,
            is_singleton=False,
            quantity=3,
            eve_type=self.item_type_1,
        )
        CharacterContractItem.objects.create(
            contract=contract,
            record_id=2,
            is_included=True,
            is_singleton=False,
            quantity=3,
            eve_type=self.item_type_2,
        )
        EveMarketPrice.objects.create(eve_type=self.item_type_1, average_price=5000000)
        request = self.factory.get(
            reverse(
                "memberaudit:character_contract_items_requested_data",
                args=[self.character.pk, contract.pk],
            )
        )
        request.user = self.user
        response = character_contract_items_requested_data(
            request, self.character.pk, contract.pk
        )
        self.assertEqual(response.status_code, 200)
        data = json_response_to_dict(response)

        self.assertSetEqual(set(data.keys()), {1})
        obj = data[1]
        self.assertEqual(obj["name"]["sort"], "High-grade Snake Alpha")
        self.assertEqual(obj["quantity"], 3)
        self.assertEqual(obj["group"], "Cyberimplant")
        self.assertEqual(obj["category"], "Implant")
        self.assertEqual(obj["price"], 5000000)
        self.assertEqual(obj["total"], 15000000)
        self.assertFalse(obj["is_blueprint_copy"])


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
