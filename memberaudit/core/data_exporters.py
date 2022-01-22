"""Export Member Audit data like wallet journals to CSV files."""
import csv
import datetime as dt
import gc
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from pytz import utc

from django.conf import settings
from django.db import models
from django.utils.functional import classproperty
from django.utils.timezone import now

from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag
from app_utils.views import yesno_str

from .. import __title__
from ..app_settings import MEMBERAUDIT_DATA_EXPORT_MIN_UPDATE_AGE
from ..models import (
    CharacterContract,
    CharacterContractItem,
    CharacterWalletJournalEntry,
)

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


def export_topic_to_archive(topic: str, destination_folder: str = None) -> Path:
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
        csv_file = exporter.write_to_file(tmpdirname)
        zip_file_path = file_to_zip(csv_file, Path(destination_folder))
    gc.collect()
    return zip_file_path


def file_to_zip(source_file: Path, destination: Path) -> Path:
    """Create a zip archive from a file."""
    _create_destination_folder(destination)
    zip_file = _zip_data_file(source_file, destination)
    return zip_file


def _create_destination_folder(destination: Path) -> Path:
    if destination:
        destination = default_destination()
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def _zip_data_file(source_file: Path, destination: Path):
    zip_command = shutil.which("zip")
    if not zip_command:
        raise RuntimeError("zip command not found on this system")
    zip_path = destination / source_file.with_suffix("").name
    try:
        zip_path.with_suffix(".zip").unlink()
    except FileNotFoundError:
        pass
    out = subprocess.DEVNULL if not settings.DEBUG else None
    result = subprocess.run(
        [zip_command, "-j", zip_path.resolve(), source_file.resolve()],
        stdout=out,
        stderr=out,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to zip file: {source_file}. returncode: {result.returncode}"
        )
    zip_file = zip_path.with_suffix(".zip")
    logger.info("Created export file: %s", zip_file)
    return zip_file


def topics_and_export_files() -> List[dict]:
    """Compile list of topics and currently available export files for download."""
    export_files = _gather_export_files()
    return _compile_topics(export_files)


def _gather_export_files() -> dict:
    destination = default_destination()
    files = [file for file in destination.glob("*.zip")]
    if files:
        export_files = {}
        for file in files:
            parts = file.with_suffix("").name.split("_")
            try:
                export_files[parts[1]] = file
            except IndexError:
                pass
    else:
        export_files = {}
    return export_files


def _compile_topics(export_files):
    topics = []
    for topic in DataExporter.topics:
        export_file = export_files[topic] if topic in export_files.keys() else None
        if export_file:
            timestamp = export_file.stat().st_mtime
            last_updated_at = dt.datetime.fromtimestamp(timestamp, tz=utc)
            MEMBERAUDIT_DATA_EXPORT_MIN_UPDATE_AGE
            update_allowed = settings.DEBUG or (
                now() - last_updated_at
            ).total_seconds() > (MEMBERAUDIT_DATA_EXPORT_MIN_UPDATE_AGE * 60)
        else:
            last_updated_at = None
            update_allowed = True
        exporter = DataExporter.create_exporter(topic)
        topics.append(
            {
                "value": topic,
                "title": exporter.title,
                "rows": exporter.count(),
                "last_updated_at": last_updated_at,
                "has_file": export_file is not None,
                "update_allowed": update_allowed,
            }
        )
    return topics


def default_destination() -> Path:
    return Path(settings.BASE_DIR) / _app_name() / "data_exports"


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
    def output_basename(self) -> Path:
        return Path(f"{_app_name()}_{self.topic}")

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
        return Path(destination) / self.output_basename.with_suffix(".csv")

    def write_to_file(self, destination: str) -> Path:
        """Write export data to CSV file.

        Returns full path to CSV file.
        """
        output_file = self.output_path(destination)
        with output_file.open("w", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.fieldnames())
            writer.writeheader()
            chunk_size = 1000
            for obj in self.queryset.iterator(chunk_size=chunk_size):
                row = self.format_obj(obj)
                writer.writerow(row)
        return output_file

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
