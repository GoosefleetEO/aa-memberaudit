import csv
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import models
from django.utils.timezone import now

from app_utils.logging import LoggerAddTag

from ... import __title__
from ...models import CharacterWalletJournalEntry

logger = LoggerAddTag(logging.getLogger(__name__), __title__)


class DataExporter(ABC):
    """Base class for all data exporters."""

    @abstractmethod
    def format_row(self, row: models.Model) -> dict:
        """Format object into row for output."""
        raise NotImplementedError()

    @classmethod
    def create_exporter(cls, topic: str) -> "DataExporter":
        """Create an exporter for the requested topic."""
        if topic == WalletJournalExporter.topic:
            return WalletJournalExporter()
        raise NotImplementedError()

    def has_data(self) -> bool:
        return self.queryset.exists()

    def count(self) -> bool:
        return self.queryset.count()

    def fieldnames(self) -> dict:
        return self.format_row(self.queryset[0]).keys()

    def output_filename(self) -> str:
        return f'memberaudit_{self.topic}_{now().strftime("%Y%m%d")}.csv'


class WalletJournalExporter(DataExporter):
    topic = "wallet_journal"

    def __init__(self) -> None:
        self.queryset = CharacterWalletJournalEntry.objects.select_related(
            "first_party",
            "second_party",
            "character__character_ownership__character",
        ).order_by("date")

    def format_row(self, row: models.Model) -> dict:
        first_party = row.first_party.name if row.first_party else "-"
        second_party = row.second_party.name if row.second_party else "-"
        character = row.character.character_ownership.character
        return {
            "date": row.date.strftime("%Y-%m-%d %H:%M:%S"),
            "owner character": character.character_name,
            "owner corporation": character.corporation_name,
            "ref type": row.ref_type.replace("_", " ").title(),
            "first party": first_party,
            "second party": second_party,
            "amount": float(row.amount),
            "balance": float(row.balance),
            "description": row.description,
            "reason": row.reason,
        }


class Command(BaseCommand):
    help = "Export data into a CSV file."

    def add_arguments(self, parser):
        parser.add_argument(
            "topic",
            choices=["wallet_journal"],
            help="Section for exporting data from",
        )

    def handle(self, *args, **options):
        self.stdout.write("Member Audit - Data Export")
        self.stdout.write()
        exporter = DataExporter.create_exporter(options["topic"])
        if not exporter.has_data():
            self.stdout.write(self.style.WARNING("No objects for output."))
        path = Path(exporter.output_filename())
        objects_count = exporter.count()
        self.stdout.write(
            f"Writing {objects_count:,} objects to file: {path.resolve()}"
        )
        self.stdout.write("This can take a minute. Please stand by...")
        with path.open("w", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=exporter.fieldnames())
            writer.writeheader()
            for row in exporter.queryset:
                writer.writerow(exporter.format_row(row))
        self.stdout.write(self.style.SUCCESS("\rDone."))
