import csv
import logging

from django.core.management.base import BaseCommand
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

    def wallet_journal_data(self) -> list:
        """Generate data for output."""
        query = CharacterWalletJournalEntry.objects.select_related(
            "first_party", "second_party", "character__character_ownership__character"
        ).order_by("date")
        data = list()
        for row in query:
            first_party = row.first_party.name if row.first_party else "-"
            second_party = row.second_party.name if row.second_party else "-"
            character = row.character.character_ownership.character
            data.append(
                {
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
            )
        return data

    def handle(self, *args, **options):
        self.stdout.write("Member Audit - Data Export")
        self.stdout.write()
        self.stdout.write("Collecting data...")
        if options["topic"] == "wallet_journal":
            data = self.wallet_journal_data()
        if not data:
            self.stdout.write(self.style.WARNING("No data found."))
            return
        filename = f'memberaudit_{options["topic"]}_{now().strftime("%Y%m%d")}.csv'
        self.stdout.write(f"Writing data to file {filename}...")
        with open(filename, "w", newline="") as csv_file:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        self.stdout.write(self.style.SUCCESS("Done"))
