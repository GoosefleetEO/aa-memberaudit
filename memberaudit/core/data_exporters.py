"""Export Member Audit data like wallet journals to CSV files."""
import csv
import gc
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils.functional import classproperty
from django.utils.timezone import now

from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag
from app_utils.views import yesno_str

from .. import __title__
from ..models import (
    CharacterContract,
    CharacterContractItem,
    CharacterWalletJournalEntry,
)

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


def export_topic_to_file(topic: str, destination_folder: str = None) -> Path:
    """Export data for given topic into a zipped file in destination.

    Args:
    - topic: Name of topic to export (see DataExporter.topics)
    - destination_folder: Path for creating the zip file. Will use defaults if not specified.

    Raises:
    - RuntimeError: zip file could not be created

    Returns:
    - Path of created zip file or empty string if none was created

    Shell ouput is suppressed unless in DEBUG mode.
    """
    exporter = DataExporter.create_exporter(topic)
    if not exporter.has_data():
        return ""
    logger.info("Exported %s with %s objects", exporter, f"{exporter.count():,}")
    with tempfile.TemporaryDirectory() as tmpdirname:
        exporter.write_to_file(tmpdirname)
        zip_file_path = _produce_zip_file(destination_folder, exporter, tmpdirname)
    gc.collect()
    return zip_file_path


def _produce_zip_file(
    destination_folder: str, exporter: "DataExporter", tmpdirname: str
) -> Path:
    if not destination_folder:
        destination = default_destination()
    else:
        destination = Path(destination_folder)
    destination.mkdir(parents=True, exist_ok=True)
    _delete_old_data_file(exporter, destination)
    zip_file = _zip_data_file(exporter, tmpdirname, destination)
    return zip_file


def _zip_data_file(exporter, tmpdirname, destination):
    zip_command = shutil.which("zip")
    if not zip_command:
        raise RuntimeError("zip command not found on this system")
    zip_path = exporter.output_path(destination).with_suffix("")
    csv_path = exporter.output_path(tmpdirname)
    out = subprocess.DEVNULL if not settings.DEBUG else None
    result = subprocess.run(
        [zip_command, "-j", zip_path.resolve(), csv_path.resolve()],
        stdout=out,
        stderr=out,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to create export file for {exporter} in {zip_path}. "
            f"returncode: {result.returncode}"
        )
    zip_file = zip_path.with_suffix(".zip").resolve()
    logger.info("Created export file for %s: %s", exporter, zip_file)
    return zip_file


def _delete_old_data_file(exporter, destination):
    for file in destination.glob(f"{exporter.output_filebase}_*.zip"):
        file.unlink()
        logger.info("Deleted outdated export file: %s", file)


def default_destination() -> Path:
    return Path(settings.BASE_DIR) / f"{_app_name()}_export"


class DataExporter(ABC):
    """Base class for all data exporters."""

    def __init__(self) -> None:
        self.queryset = self.get_queryset()
        self._now = now()
        if not hasattr(self, "topic"):
            raise ValueError("You must define topic.")
        if "_" in self.topic:
            raise ValueError("Topic can not contain underscores")

    def __str__(self) -> str:
        return str(self.topic)

    @property
    def title(self) -> str:
        return self.topic.replace("-", " ").title()

    @property
    def output_filebase(self) -> str:
        return f"{_app_name()}_{self.topic}"

    @property
    def output_filename(self) -> str:
        return f'{self.output_filebase}_{self._now.strftime("%Y%m%d%H%M")}.csv'

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
        return self.format_obj(self.queryset.first()).keys()

    def output_path(self, destination: str) -> Path:
        return Path(destination) / Path(self.output_filename)

    def write_to_file(self, destination: str):
        path = self.output_path(destination)
        with path.open("w", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.fieldnames())
            writer.writeheader()
            chunk_size = 1000
            for obj in self.queryset.iterator(chunk_size=chunk_size):
                row = self.format_obj(obj)
                writer.writerow(row)

    @classproperty
    def exporters(cls) -> list:
        """Provide list of supported exporters."""
        return [ContractExporter, ContractItemExporter, WalletJournalExporter]

    @classproperty
    def topics(cls) -> list:
        return [exporter.topic for exporter in cls.exporters]

    @classmethod
    def create_exporter(cls, topic: str) -> "DataExporter":
        """Create an exporter for the requested topic."""
        for exporter in cls.exporters:
            if topic == exporter.topic:
                return exporter()
        raise NotImplementedError()


class WalletJournalExporter(DataExporter):
    topic = "wallet-journal"

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
            "first party": _name_or_default(obj.first_party),
            "second party": _name_or_default(obj.second_party),
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
            "date issued": _date_or_default(obj.date_issued),
            "date expired": _date_or_default(obj.date_expired),
            "date accepted": _date_or_default(obj.date_accepted),
            "date completed": _date_or_default(obj.date_completed),
            "availability": obj.get_availability_display(),
            "issuer": obj.issuer.name,
            "issuer corporation": _name_or_default(obj.issuer_corporation),
            "acceptor": _name_or_default(obj.acceptor),
            "assignee": _name_or_default(obj.assignee),
            "reward": _value_or_default(obj.reward),
            "collateral": _value_or_default(obj.collateral),
            "volume": _value_or_default(obj.volume),
            "days to complete": _value_or_default(obj.days_to_complete),
            "start location": _value_or_default(obj.start_location),
            "end location": _value_or_default(obj.end_location),
            "price": _value_or_default(obj.price),
            "buyout": _value_or_default(obj.buyout),
            "title": obj.title,
        }


class ContractItemExporter(DataExporter):
    topic = "contract-item"

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
            "raw quantity": _value_or_default(obj.raw_quantity),
        }


def _app_name() -> str:
    return str(CharacterContract._meta.app_label)


def _name_or_default(obj: object, default: str = "") -> str:
    if obj is None:
        return default
    return obj.name


def _value_or_default(value: object, default: str = "") -> str:
    if value is None:
        return default
    return value


def _date_or_default(value: object, default: str = "") -> str:
    if value is None:
        return default
    return value.strftime("%Y-%m-%d %H:%M:%S")
