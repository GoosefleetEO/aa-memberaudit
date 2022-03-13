from django.test import RequestFactory, TestCase
from django.urls import reverse
from eveuniverse.models import EveEntity

from app_utils.testing import generate_invalid_pk, json_response_to_python

from ..models import CharacterMail
from ..views.character_viewer import (
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
from .utils import create_memberaudit_character

CHARACTER_VIEWER_PATH = "memberaudit.views.character_viewer"


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
