"""Factories for creating test objects with defaults."""
import datetime as dt
from random import randint
from typing import Iterable

from django.db import models
from django.utils.timezone import now

from ...models import (
    Character,
    CharacterContract,
    CharacterContractItem,
    CharacterMail,
    CharacterMailLabel,
    CharacterWalletJournalEntry,
    MailEntity,
)


def create_character(**kwargs):
    return Character.objects.create(**kwargs)


def create_character_mail(
    recipients: Iterable[MailEntity] = None,
    labels: Iterable[CharacterMailLabel] = None,
    **kwargs,
):
    timestamp = now() if "timestamp" not in kwargs else kwargs["timestamp"]
    params = {
        "subject": "Test Mail",
        "body": "Test Body",
        "timestamp": timestamp,
    }
    if "mail_id" not in kwargs:
        params["mail_id"] = _generate_unique_id(CharacterMail, "mail_id")
    if "sender" not in kwargs and "sender_id" not in kwargs:
        params["sender"] = create_mail_entity_from_eve_entity(id=1002)
    params.update(kwargs)
    obj = CharacterMail.objects.create(**params)
    if not recipients:
        character = kwargs["character"]
        character_id = character.character_ownership.character.character_id
        recipients = [create_mail_entity_from_eve_entity(id=character_id)]
    obj.recipients.add(*recipients)
    if labels:
        obj.labels.add(*labels)
    return obj


def create_character_mail_label(**kwargs):
    label_id = _generate_unique_id(CharacterMailLabel, "label_id")
    params = {
        "label_id": label_id,
        "name": f"Label #{label_id}",
    }
    params.update(kwargs)
    return CharacterMailLabel.objects.create(**params)


def create_contract(**kwargs) -> models.Model:
    date_issed = now() if "date_issued" not in kwargs else kwargs["date_issued"]
    params = {
        "contract_id": _generate_unique_id(CharacterContract, "contract_id"),
        "availability": CharacterContract.AVAILABILITY_PERSONAL,
        "contract_type": CharacterContract.TYPE_ITEM_EXCHANGE,
        "assignee_id": 1002,
        "date_issued": date_issed,
        "date_expired": date_issed + dt.timedelta(days=3),
        "for_corporation": False,
        "issuer_id": 1001,
        "issuer_corporation_id": 2001,
        "status": CharacterContract.STATUS_OUTSTANDING,
        "title": "Dummy info",
    }
    params.update(kwargs)
    return CharacterContract.objects.create(**params)


def create_contract_item(**kwargs) -> models.Model:
    params = {
        "record_id": _generate_unique_id(CharacterContractItem, "record_id"),
        "is_included": True,
        "is_singleton": False,
        "quantity": 1,
        "eve_type_id": 603,
    }
    params.update(kwargs)
    return CharacterContractItem.objects.create(**params)


def create_mail_entity_from_eve_entity(id: int):
    obj, _ = MailEntity.objects.update_or_create_from_eve_entity_id(id=id)
    return obj


def create_mailing_list(**kwargs):
    my_id = _generate_unique_id(MailEntity, "id")
    params = {
        "id": my_id,
        "name": f"Mailing List #{my_id}",
        "category": MailEntity.Category.MAILING_LIST,
    }
    params.update(kwargs)
    return MailEntity.objects.create(**params)


def create_wallet_journal_entry(**kwargs) -> models.Model:
    params = {
        "entry_id": _generate_unique_id(CharacterWalletJournalEntry, "entry_id"),
        "amount": 1000000.0,
        "balance": 20000000.0,
        "ref_type": "player_donation",
        "context_id_type": CharacterWalletJournalEntry.CONTEXT_ID_TYPE_UNDEFINED,
        "date": now(),
        "description": "test description",
        "first_party_id": 1001,
        "second_party_id": 1002,
        "reason": "test reason",
    }
    params.update(kwargs)
    return CharacterWalletJournalEntry.objects.create(**params)


def _generate_unique_id(Model: object, field_name: str):
    while True:
        id = randint(1, 2_000_000_000)
        params = {field_name: id}
        if not Model.objects.filter(**params).exists():
            return id
