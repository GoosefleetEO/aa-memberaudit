import datetime as dt
from typing import Iterable, List, Tuple

from bravado.exception import HTTPForbidden, HTTPUnauthorized

from django.contrib.auth.models import Group, User
from django.db import models, transaction
from django.db.models import Q
from django.utils.timezone import now
from esi.models import Token
from eveuniverse.models import EveEntity, EveSolarSystem, EveType

from allianceauth.notifications import notify
from allianceauth.services.hooks import get_extension_logger
from app_utils.esi import fetch_esi_status
from app_utils.logging import LoggerAddTag

from .. import __title__
from ..app_settings import (
    MEMBERAUDIT_BULK_METHODS_BATCH_SIZE,
    MEMBERAUDIT_LOCATION_STALE_HOURS,
)
from ..constants import DATETIME_FORMAT, EveCategoryId, EveTypeId
from ..core.fittings import Fitting
from ..core.skill_plans import SkillPlan
from ..core.skills import Skill
from ..helpers import filter_groups_available_to_user
from ..providers import esi

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


class ComplianceGroupDesignationManager(models.Manager):
    def groups(self) -> models.QuerySet:
        """Groups which are compliance groups."""
        return Group.objects.filter(compliancegroupdesignation__isnull=False)

    def update_user(self, user: User):
        """Update compliance groups for user."""
        from ..models import General

        was_compliant = user.groups.filter(
            compliancegroupdesignation__isnull=False
        ).exists()
        is_compliant = General.compliant_users().filter(pk=user.pk).exists()
        if is_compliant:
            # adding groups one by one due to Auth issue #1268
            # TODO: Refactor once issue is fixed
            groups_qs = filter_groups_available_to_user(self.groups(), user).exclude(
                user=user
            )
            for group in groups_qs:
                user.groups.add(group)
            if groups_qs.exists() and not was_compliant:
                logger.info("%s: User is now compliant", user)
                message = (
                    f"Thank you for registering all your characters to {__title__}. "
                    "You now have gained access to additional services."
                )
                notify(
                    user,
                    title=f"{__title__}: All characters registered",
                    message=message,
                    level="success",
                )
        else:
            # removing groups one by one due to Auth issue #1268
            # TODO: Refactor once issue is fixed
            current_groups_qs = self.filter(group__user=user).values_list(
                "group", flat=True
            )
            for group in current_groups_qs:
                user.groups.remove(group)
            if was_compliant:
                logger.info("%s: User is no longer compliant", user)
                message = (
                    f"Some of your characters are not registered to {__title__} "
                    "and you have therefore lost access to services. "
                    "Please add missing characters to restore access."
                )
                notify(
                    user,
                    title=f"{__title__}: Characters not registered",
                    message=message,
                    level="warning",
                )


class EveShipTypeManger(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("eve_group")
            .filter(published=True)
            .filter(eve_group__eve_category_id=EveCategoryId.SHIP)
        )


class EveSkillTypeManger(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(published=True)
            .filter(eve_group__eve_category_id=EveCategoryId.SKILL)
        )


class LocationManager(models.Manager):
    """Manager for Location model

    We recommend preferring the "async" variants, because it includes protection
    against exceeding the ESI error limit due to characters no longer having access
    to structures within their assets, contracts, etc.

    The async methods will first create an empty location and then try to
    update that empty location asynchronously from ESI.
    Updates might be delayed if the error limit is reached.

    The async method can also be used safely in mass updates, where the same
    unauthorized update might be requested multiple times.
    Additional requests for the same location will be ignored within a grace period.
    """

    _UPDATE_EMPTY_GRACE_MINUTES = 5

    def get_or_create_esi(self, id: int, token: Token) -> Tuple[models.Model, bool]:
        """gets or creates location object with data fetched from ESI

        Stale locations will always be updated.
        Empty locations will always be updated after grace period as passed
        """
        return self._get_or_create_esi(id=id, token=token, update_async=False)

    def get_or_create_esi_async(
        self, id: int, token: Token
    ) -> Tuple[models.Model, bool]:
        """gets or creates location object with data fetched from ESI asynchronous"""
        return self._get_or_create_esi(id=id, token=token, update_async=True)

    def _get_or_create_esi(
        self, id: int, token: Token, update_async: bool = True
    ) -> Tuple[models.Model, bool]:
        id = int(id)
        empty_threshold = now() - dt.timedelta(minutes=self._UPDATE_EMPTY_GRACE_MINUTES)
        stale_threshold = now() - dt.timedelta(hours=MEMBERAUDIT_LOCATION_STALE_HOURS)
        try:
            location = self.exclude(
                (Q(eve_type__isnull=True) & Q(updated_at__lt=empty_threshold))
                | Q(updated_at__lt=stale_threshold)
            ).get(id=id)
            created = False
            return location, created
        except self.model.DoesNotExist:
            if update_async:
                return self.update_or_create_esi_async(id=id, token=token)
            return self.update_or_create_esi(id=id, token=token)

    def update_or_create_esi_async(
        self, id: int, token: Token
    ) -> Tuple[models.Model, bool]:
        """updates or creates location object with data fetched from ESI asynchronous"""
        return self._update_or_create_esi(id=id, token=token, update_async=True)

    def update_or_create_esi(self, id: int, token: Token) -> Tuple[models.Model, bool]:
        """updates or creates location object with data fetched from ESI synchronous

        The preferred method to use is: `update_or_create_esi_async()`,
        since it protects against exceeding the ESI error limit and which can happen
        a lot due to users not having authorization to access a structure.
        """
        return self._update_or_create_esi(id=id, token=token, update_async=False)

    def _update_or_create_esi(
        self, id: int, token: Token, update_async: bool = True
    ) -> Tuple[models.Model, bool]:
        id = int(id)
        if self.model.is_asset_safety_id(id):
            eve_type, _ = EveType.objects.get_or_create_esi(
                id=EveTypeId.ASSET_SAFETY_WRAP
            )
            return self.update_or_create(
                id=id,
                defaults={"name": "ASSET SAFETY", "eve_type": eve_type},
            )
        elif self.model.is_solar_system_id(id):
            eve_solar_system, _ = EveSolarSystem.objects.get_or_create_esi(id=id)
            eve_type, _ = EveType.objects.get_or_create_esi(id=EveTypeId.SOLAR_SYSTEM)
            return self.update_or_create(
                id=id,
                defaults={
                    "name": eve_solar_system.name,
                    "eve_solar_system": eve_solar_system,
                    "eve_type": eve_type,
                },
            )
        elif self.model.is_station_id(id):
            logger.info("%s: Fetching station from ESI", id)
            station = esi.client.Universe.get_universe_stations_station_id(
                station_id=id
            ).results()
            return self._station_update_or_create_dict(id=id, station=station)
        elif self.model.is_structure_id(id):
            if update_async:
                return self._structure_update_or_create_esi_async(id=id, token=token)
            return self.structure_update_or_create_esi(id=id, token=token)
        logger.warning(
            "%s: Creating empty location for ID not matching any known pattern:", id
        )
        return self.get_or_create(id=id)

    def _station_update_or_create_dict(
        self, id: int, station: dict
    ) -> Tuple[models.Model, bool]:
        if station.get("system_id"):
            eve_solar_system, _ = EveSolarSystem.objects.get_or_create_esi(
                id=station.get("system_id")
            )
        else:
            eve_solar_system = None

        if station.get("type_id"):
            eve_type, _ = EveType.objects.get_or_create_esi(id=station.get("type_id"))
        else:
            eve_type = None

        if station.get("owner"):
            owner, _ = EveEntity.objects.get_or_create_esi(id=station.get("owner"))
        else:
            owner = None

        return self.update_or_create(
            id=id,
            defaults={
                "name": station.get("name", ""),
                "eve_solar_system": eve_solar_system,
                "eve_type": eve_type,
                "owner": owner,
            },
        )

    def _structure_update_or_create_esi_async(self, id: int, token: Token):
        from ..tasks import DEFAULT_TASK_PRIORITY
        from ..tasks import update_structure_esi as task_update_structure_esi

        id = int(id)
        location, created = self.get_or_create(id=id)
        task_update_structure_esi.apply_async(
            kwargs={"id": id, "token_pk": token.pk},
            priority=DEFAULT_TASK_PRIORITY,
        )
        return location, created

    def structure_update_or_create_esi(self, id: int, token: Token):
        """Update or creates structure from ESI"""
        fetch_esi_status().raise_for_status()
        try:
            structure = esi.client.Universe.get_universe_structures_structure_id(
                structure_id=id, token=token.valid_access_token()
            ).results()
        except (HTTPUnauthorized, HTTPForbidden) as http_error:
            logger.warn(
                "%s: No access to structure #%s: %s",
                token.character_name,
                id,
                http_error,
            )
            return self.get_or_create(id=id)
        else:
            return self._structure_update_or_create_dict(id=id, structure=structure)

    def _structure_update_or_create_dict(
        self, id: int, structure: dict
    ) -> Tuple[models.Model, bool]:
        """creates a new Location object from a structure dict"""
        if structure.get("solar_system_id"):
            eve_solar_system, _ = EveSolarSystem.objects.get_or_create_esi(
                id=structure.get("solar_system_id")
            )
        else:
            eve_solar_system = None

        if structure.get("type_id"):
            eve_type, _ = EveType.objects.get_or_create_esi(id=structure.get("type_id"))
        else:
            eve_type = None

        if structure.get("owner_id"):
            owner, _ = EveEntity.objects.get_or_create_esi(id=structure.get("owner_id"))
        else:
            owner = None

        return self.update_or_create(
            id=id,
            defaults={
                "name": structure.get("name", ""),
                "eve_solar_system": eve_solar_system,
                "eve_type": eve_type,
                "owner": owner,
            },
        )


class SkillSetManager(models.Manager):
    def update_or_create_from_fitting(
        self,
        fitting: Fitting,
        user: User = None,
        skill_set_group=None,
        skill_set_name=None,
    ) -> Tuple[models.Model, bool]:
        """Update or create a skill set from a fitting."""
        if not skill_set_name:
            skill_set_name = fitting.name
        return self.update_or_create_from_skills(
            name=skill_set_name,
            skills=fitting.required_skills(),
            source=f"EFT fitting '{fitting.name}'",
            user=user,
            skill_set_group=skill_set_group,
            ship_type=fitting.ship_type,
        )

    def update_or_create_from_skill_plan(
        self, skill_plan: SkillPlan, user: User = None, skill_set_group=None
    ) -> Tuple[models.Model, bool]:
        """Update or create a skill set from a fitting."""

        return self.update_or_create_from_skills(
            name=skill_plan.name,
            skills=skill_plan.skills,
            source="imported skill plan",
            user=user,
            skill_set_group=skill_set_group,
        )

    def update_or_create_from_skills(
        self,
        name: str,
        skills: List[Skill],
        source: str,
        user: User = None,
        skill_set_group=None,
        ship_type: EveType = None,
    ) -> Tuple[models.Model, bool]:
        """Update or create a skill set from skills."""
        from ..models import SkillSetSkill

        description = (
            f"Generated from {source} "
            f"by {user if user else '?'} "
            f"at {now().strftime(DATETIME_FORMAT)}"
        )
        with transaction.atomic():
            skill_set, created = self.update_or_create(
                name=name, defaults={"description": description, "ship_type": ship_type}
            )
            skill_set.skills.all().delete()
            skill_set_skills = [
                SkillSetSkill(
                    skill_set=skill_set,
                    eve_type=skill.eve_type,
                    required_level=skill.level,
                )
                for skill in skills
            ]
            SkillSetSkill.objects.bulk_create(skill_set_skills)
            if skill_set_group:
                skill_set_group.skill_sets.add(skill_set)
        return skill_set, created

    def compile_groups_map(self) -> dict:
        """Compiles map of all skill sets by groups."""

        def _add_skill_set(groups_map, skill_set, group=None):
            group_id = group.id if group else 0
            if group_id not in groups_map.keys():
                groups_map[group_id] = {"group": group, "skill_sets": []}
            groups_map[group_id]["skill_sets"].append(skill_set)

        groups_map = dict()
        for skill_set in (
            self.select_related("ship_type").prefetch_related("groups").all()
        ):
            if skill_set.groups.exists():
                for group in skill_set.groups.all():
                    _add_skill_set(groups_map, skill_set, group)
            else:
                _add_skill_set(groups_map, skill_set, group=None)
        return groups_map
