import csv
import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now

from app_utils.logging import LoggerAddTag

from ... import __title__
from ...models import CharacterWalletJournalEntry

logger = LoggerAddTag(logging.getLogger(__name__), __title__)


class Command(BaseCommand):
    help = "Export data into a CSV file."

    def add_arguments(self, parser):
        parser.add_argument(
            "topic",
            choices=["wallet_journal"],
            help="Section for exporting data from",
        )

    def wallet_journal_formatter(self, row: object) -> dict:
        """Format wallet journal object into row for output."""
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

    def handle(self, *args, **options):
        self.stdout.write("Member Audit - Data Export")
        self.stdout.write()
        if options["topic"] == "wallet_journal":
            query = CharacterWalletJournalEntry.objects.select_related(
                "first_party",
                "second_party",
                "character__character_ownership__character",
            ).order_by("date")
            formatter = self.wallet_journal_formatter
        else:
            raise CommandError("Invalid topic selected.")
        if not query.exists():
            self.stdout.write(self.style.WARNING("No objects for output."))
        filename = f'memberaudit_{options["topic"]}_{now().strftime("%Y%m%d")}.csv'
        path = Path(filename)
        objects_count = query.count()
        self.stdout.write(f"Writing {objects_count} objects to file: {path.resolve()}")
        n = 0
        with path.open("w", newline="") as csv_file:
            fieldnames = formatter(query[0]).keys()
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in query:
                writer.writerow(formatter(row))
                self.stdout.write(f"\r{int(n / objects_count * 100)}%", ending="")
                n += 1
        self.stdout.write(self.style.SUCCESS("\rDone."))
