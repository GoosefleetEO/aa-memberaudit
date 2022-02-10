import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand

from app_utils.logging import LoggerAddTag

from ... import __title__
from ...constants import EveCategoryId

logger = LoggerAddTag(logging.getLogger(__name__), __title__)


class Command(BaseCommand):
    help = "Preloads data required for this app from ESI"

    def handle(self, *args, **options):
        call_command(
            "eveuniverse_load_types",
            __title__,
            "--category_id",
            str(EveCategoryId.BLUEPRINT.value),
            "--category_id",
            str(EveCategoryId.SHIP.value),
            "--category_id",
            str(EveCategoryId.MODULE.value),
            "--category_id",
            str(EveCategoryId.CHARGE.value),
            "--category_id",
            str(EveCategoryId.SKILL.value),
            "--category_id",
            str(EveCategoryId.DRONE.value),
            "--category_id_with_dogma",
            str(EveCategoryId.IMPLANT.value),
            "--category_id",
            str(EveCategoryId.FIGHTER.value),
            "--category_id",
            str(EveCategoryId.STRUCTURE.value),
        )
