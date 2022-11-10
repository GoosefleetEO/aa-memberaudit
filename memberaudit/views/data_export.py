import csv
import datetime as dt

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import F
from django.http import Http404, StreamingHttpResponse
from django.shortcuts import redirect, render

from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag

from .. import __title__
from ..forms import DataExportForm
from ..models import (
    Character,
    CharacterAsset,
    CharacterContact,
    CharacterContract,
    CharacterMiningLedgerEntry,
    CharacterSkill,
    CharacterWalletJournalEntry,
    CharacterWalletTransaction,
)
from ._common import add_common_context

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


@login_required
@permission_required("memberaudit.exports_access")
def data_export(request):
    if request.method == "POST":
        form = DataExportForm(request.POST)
        if form.is_valid():
            topic = form.cleaned_data["topic"]
            return redirect("memberaudit:download_csv", topic)
    else:
        form = DataExportForm()
    context = {
        "page_title": "Data Export",
        "form": form,
        "characters_count": Character.objects.user_has_access(request.user).count(),
    }
    return render(
        request, "memberaudit/data_export.html", add_common_context(request, context)
    )


@login_required
@permission_required("memberaudit.exports_access")
def download_csv(request, topic: str) -> StreamingHttpResponse:
    """Stream selected data for selected topic as CSV file
    and respect character scope of current user.
    """
    topic_map = {
        DataExportForm.Topic.ASSETS: CharacterAsset,
        DataExportForm.Topic.CONTACTS: CharacterContact,
        DataExportForm.Topic.CONTRACTS: CharacterContract,
        DataExportForm.Topic.MINING_LEDGER: CharacterMiningLedgerEntry,
        DataExportForm.Topic.SKILLS: CharacterSkill,
        DataExportForm.Topic.WALLET_JOURNAL: CharacterWalletJournalEntry,
        DataExportForm.Topic.WALLET_TRANSACTIONS: CharacterWalletTransaction,
    }
    try:
        MyModel = topic_map[topic]
    except KeyError:
        raise Http404(f"Data export not defined for topic: {topic}") from None
    character_pks = Character.objects.user_has_access(request.user).values_list(
        "pk", flat=True
    )
    queryset = (
        MyModel.objects.filter(character__pk__in=character_pks)
        .annotate(character_corporation=F("character__eve_character__corporation_name"))
        .select_related()
        .order_by("pk")
    )
    logger.info("Preparing to export the with %s entries.", queryset.count())
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    return StreamingHttpResponse(
        (writer.writerow(row) for row in _csv_line_generator(queryset)),
        content_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{topic}.csv"'},
    )


def _csv_line_generator(queryset):
    """Return the objects of a queryset for a CSV file line by line as generator.
    Starting with the list of field names as first line.

    First column is always "id".
    Other columns are sorted by name.
    Annotations are included.
    """
    obj = queryset.first()
    if not obj:
        return ""
    field_name_map = {k: v["name"].title() for k, v in _obj_asdict(obj).items()}
    obj_field_names = [key for key in field_name_map.keys() if key != "id"]
    annotations = list(queryset.query.annotations.keys())
    for key in annotations:
        field_name_map[key] = key.replace("_", " ").title()
    field_names = ["id"] + sorted(obj_field_names + annotations)
    yield [field_name_map[key] for key in field_names]

    for obj in queryset.iterator():
        data = _obj_asdict(obj)
        for key in annotations:
            data[key] = {"name": key, "value": getattr(obj, key)}
        yield [data[key]["value"] for key in field_names]


def _obj_asdict(obj) -> dict:
    """Convert to representation as Python dict."""
    struct = {}
    for field in obj._meta.fields:
        if field.choices:
            value = getattr(obj, f"get_{field.name}_display")()
        else:
            value = getattr(obj, field.name)
        # if callable(value):
        #     try:
        #         value = value() or ""
        #     except Exception:
        #         value = "Error retrieving value"
        if isinstance(value, dt.datetime):
            value = value.strftime("%Y-%m-%d %H:%M:%S")
        if value is None:
            value = ""
        struct[field.name] = {"name": field.verbose_name, "value": value}
    return struct
