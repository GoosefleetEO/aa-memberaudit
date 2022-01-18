import csv
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import models
from django.utils.functional import classproperty
from django.utils.timezone import now

from app_utils.logging import LoggerAddTag
from app_utils.views import yesno_str

from ... import __title__
from ...models import (
    CharacterContract,
    CharacterContractItem,
    CharacterWalletJournalEntry,
)

logger = LoggerAddTag(logging.getLogger(__name__), __title__)


def name_or_default(obj: object, default: str = "") -> str:
    if obj is None:
        return default
    return obj.name


def value_or_default(value: object, default: str = "") -> str:
    if value is None:
        return default
    return value


def date_or_default(value: object, default: str = "") -> str:
    if value is None:
        return default
    return value.strftime("%Y-%m-%d %H:%M:%S")


class DataExporter(ABC):
    """Base class for all data exporters."""

    def __init__(self) -> None:
        self.queryset = self.get_queryset()

    @abstractmethod
    def get_queryset(self) -> models.QuerySet:
        """Return queryset to fetch the data for this exporter."""
        raise NotImplementedError()

    @abstractmethod
    def format_obj(self, obj: models.Model) -> dict:
        """Format object into row for output."""
        raise NotImplementedError()

    def has_data(self) -> bool:
        return self.queryset.exists()

    def count(self) -> bool:
        return self.queryset.count()

    def fieldnames(self) -> dict:
        return self.format_obj(self.queryset[0]).keys()

    def output_filename(self) -> str:
        return f'memberaudit_{self.topic}_{now().strftime("%Y%m%d")}.csv'

    @classproperty
    def _exporters(cls) -> list:
        """Provide list of supported exporters."""
        return [WalletJournalExporter, ContractExporter, ContractItemExporter]

    @classproperty
    def topics(cls) -> list:
        return [exporter.topic for exporter in cls._exporters]

    @classmethod
    def create_exporter(cls, topic: str) -> "DataExporter":
        """Create an exporter for the requested topic."""
        for exporter in cls._exporters:
            if topic == exporter.topic:
                return exporter()
        raise NotImplementedError()


class WalletJournalExporter(DataExporter):
    topic = "wallet_journal"

    def get_queryset(self) -> models.QuerySet:
        return CharacterWalletJournalEntry.objects.select_related(
            "first_party",
            "second_party",
            "character__character_ownership__character",
        ).order_by("date")

    def format_obj(self, obj: models.Model) -> dict:
        character = obj.character.character_ownership.character
        return {
            "date": obj.date.strftime("%Y-%m-%d %H:%M:%S"),
            "owner character": character.character_name,
            "owner corporation": character.corporation_name,
            "ref type": obj.ref_type.replace("_", " ").title(),
            "first party": name_or_default(obj.first_party),
            "second party": name_or_default(obj.second_party),
            "amount": float(obj.amount),
            "balance": float(obj.balance),
            "description": obj.description,
            "reason": obj.reason,
        }


class ContractExporter(DataExporter):
    topic = "contract"

    def get_queryset(self) -> models.QuerySet:
        return CharacterContract.objects.select_related(
            "acceptor",
            "acceptor_corporation",
            "assignee",
            "end_location",
            "issuer_corporation",
            "issuer",
            "start_location",
            "character__character_ownership__character",
        ).order_by("date_issued")

    def format_obj(self, obj: models.Model) -> dict:
        character = obj.character.character_ownership.character
        return {
            "owner character": character.character_name,
            "owner corporation": character.corporation_name,
            "contract pk": obj.pk,
            "contract id": obj.contract_id,
            "contract_type": obj.get_contract_type_display(),
            "status": obj.get_status_display(),
            "date issued": date_or_default(obj.date_issued),
            "date expired": date_or_default(obj.date_expired),
            "date accepted": date_or_default(obj.date_accepted),
            "date completed": date_or_default(obj.date_completed),
            "availability": obj.get_availability_display(),
            "issuer": obj.issuer.name,
            "issuer corporation": name_or_default(obj.issuer_corporation),
            "acceptor": name_or_default(obj.acceptor),
            "assignee": name_or_default(obj.assignee),
            "reward": value_or_default(obj.reward),
            "collateral": value_or_default(obj.collateral),
            "volume": value_or_default(obj.volume),
            "days to complete": value_or_default(obj.days_to_complete),
            "start location": value_or_default(obj.start_location),
            "end location": value_or_default(obj.end_location),
            "price": value_or_default(obj.price),
            "buyout": value_or_default(obj.buyout),
            "title": obj.title,
        }


class ContractItemExporter(DataExporter):
    topic = "contract_item"

    def get_queryset(self) -> models.QuerySet:
        return CharacterContractItem.objects.select_related(
            "contract", "eve_type"
        ).order_by("contract", "record_id")

    def format_obj(self, obj: models.Model) -> dict:
        return {
            "contract pk": obj.contract.pk,
            "record id": obj.record_id,
            "type": obj.eve_type.name,
            "quantity": obj.quantity,
            "is included": yesno_str(obj.is_included),
            "is singleton": yesno_str(obj.is_blueprint),
            "is blueprint": yesno_str(obj.is_blueprint_original),
            "is blueprint_original": yesno_str(obj.is_blueprint_original),
            "is blueprint_copy": yesno_str(obj.is_blueprint_copy),
            "raw quantity": value_or_default(obj.raw_quantity),
        }


class Command(BaseCommand):
    help = "Export data into a CSV file."

    def add_arguments(self, parser):
        parser.add_argument(
            "topic",
            choices=sorted(DataExporter.topics),
            help="Section for exporting data from",
        )
        parser.add_argument(
            "--destination",
            default=str(Path.cwd().resolve()),
            help="Directory the output file will be written to",
        )

    def handle(self, *args, **options):
        self.stdout.write("Member Audit - Data Export")
        self.stdout.write()
        exporter = DataExporter.create_exporter(options["topic"])
        if not exporter.has_data():
            self.stdout.write(self.style.WARNING("No objects for output."))
        path = Path(options["destination"]) / Path(exporter.output_filename())
        objects_count = exporter.count()
        self.stdout.write(
            f"Writing {objects_count:,} objects to file: {path.resolve()}"
        )
        self.stdout.write("This can take a minute. Please stand by...")
        with path.open("w", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=exporter.fieldnames())
            writer.writeheader()
            for obj in exporter.queryset:
                writer.writerow(exporter.format_obj(obj))
        self.stdout.write(self.style.SUCCESS("Done."))
