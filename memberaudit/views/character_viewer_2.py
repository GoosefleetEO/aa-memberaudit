import datetime as dt
from typing import Optional

import humanize

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext, gettext_lazy
from eveuniverse.core import eveimageserver
from eveuniverse.models import EveType

from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag
from app_utils.views import bootstrap_label_html, yesnonone_str

from .. import __title__
from ..constants import (
    DATETIME_FORMAT,
    DEFAULT_ICON_SIZE,
    MAP_ARABIC_TO_ROMAN_NUMBERS,
    SKILL_SET_DEFAULT_ICON_TYPE_ID,
)
from ..decorators import fetch_character_if_allowed
from ..models import Character, SkillSet, SkillSetSkill
from ._common import UNGROUPED_SKILL_SET

logger = LoggerAddTag(get_extension_logger(__name__), __title__)

ICON_SIZE_64 = 64
CHARACTER_VIEWER_DEFAULT_TAB = "mails"

ICON_FAILED = "fas fa-times boolean-icon-false"
ICON_PARTIAL = "fas fa-check text-warning"
ICON_FULL = "fas fa-check-double text-success"
ICON_MET_ALL_REQUIRED = "fas fa-check text-success"


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_skillqueue_data(
    request, character_pk: int, character: Character
) -> JsonResponse:
    data = list()
    try:
        for row in character.skillqueue.select_related("eve_type").filter(
            character_id=character_pk
        ):
            level_roman = MAP_ARABIC_TO_ROMAN_NUMBERS[row.finished_level]
            skill_str = f"{row.eve_type.name}&nbsp;{level_roman}"
            if row.is_active:
                skill_str += " [ACTIVE]"

            if row.finish_date:
                finish_date_humanized = humanize.naturaltime(
                    dt.datetime.now()
                    + dt.timedelta(
                        seconds=(
                            row.finish_date.timestamp() - dt.datetime.now().timestamp()
                        )
                    )
                )
                finish_date_str = (
                    f"{row.finish_date.strftime(DATETIME_FORMAT)} "
                    f"({finish_date_humanized})"
                )
                finish_date_sort = row.finish_date.isoformat()
            else:
                finish_date_str = gettext("(training not active)")
                finish_date_sort = None

            data.append(
                {
                    "position": row.queue_position + 1,
                    "skill": skill_str,
                    "finished": {
                        "display": finish_date_str,
                        "sort": finish_date_sort,
                    },
                    "is_active": row.is_active,
                }
            )
    except ObjectDoesNotExist:
        pass

    return JsonResponse(data, safe=False)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_skill_sets_data(
    request, character_pk: int, character: Character
) -> JsonResponse:
    def create_data_row(check, group) -> dict:
        if group:
            group_name = (
                group.name_plus if group.is_active else group.name + " [Not active]"
            )
        else:
            group_name = UNGROUPED_SKILL_SET

        url = (
            check.skill_set.ship_type.icon_url(
                DEFAULT_ICON_SIZE, variant=EveType.IconVariant.REGULAR
            )
            if check.skill_set.ship_type
            else eveimageserver.type_icon_url(
                SKILL_SET_DEFAULT_ICON_TYPE_ID, size=DEFAULT_ICON_SIZE
            )
        )
        ship_icon = f'<img width="24" heigh="24" src="{url}"/>'
        failed_required_skills = compile_failed_skills(
            check.failed_required_skills, "required_level"
        )
        has_required = (
            not bool(failed_required_skills)
            if failed_required_skills is not None
            else None
        )
        failed_recommended_skills = compile_failed_skills(
            check.failed_recommended_skills, "recommended_level"
        )
        has_recommended = (
            not bool(failed_recommended_skills)
            if failed_recommended_skills is not None
            else None
        )
        ajax_children_url = reverse(
            "memberaudit:character_skill_set_details",
            args=[character.pk, check.skill_set_id],
        )

        actions_html = (
            '<button type="button" class="btn btn-primary" '
            'data-toggle="modal" data-target="#modalCharacterSkillSetDetails" '
            f"data-ajax_skill_set_detail={ ajax_children_url }>"
            '<i class="fas fa-search"></i></button>'
        )

        return {
            "id": check.id,
            "group": group_name,
            "skill_set": ship_icon + "&nbsp;&nbsp;" + check.skill_set.name,
            "skill_set_name": check.skill_set.name,
            "is_doctrine_str": yesnonone_str(group.is_doctrine if group else False),
            "failed_required_skills": format_failed_skills(failed_required_skills),
            "has_required": has_required,
            "has_required_str": yesnonone_str(has_required),
            "failed_recommended_skills": format_failed_skills(
                failed_recommended_skills
            ),
            "has_recommended": has_recommended,
            "has_recommended_str": yesnonone_str(has_recommended),
            "action": actions_html,
        }

    def compile_failed_skills(failed_skills, level_name) -> Optional[list]:
        failed_skills = sorted(
            failed_skills.values("eve_type__name", level_name),
            key=lambda k: k["eve_type__name"].lower(),
        )
        return [
            bootstrap_label_html(
                format_html(
                    "{}&nbsp;{}",
                    obj["eve_type__name"],
                    MAP_ARABIC_TO_ROMAN_NUMBERS[obj[level_name]],
                ),
                "default",
            )
            for obj in failed_skills
        ]

    def format_failed_skills(skills) -> str:
        return " ".join(skills) if skills else "-"

    data = list()
    try:
        for check in character.skill_set_checks.filter(
            skill_set__is_visible=True
        ).select_related(
            "skill_set", "skill_set__ship_type", "skill_set__ship_type__eve_group"
        ):
            if not check.skill_set.groups.exists():
                data.append(create_data_row(check, None))
            else:
                for group in check.skill_set.groups.all():
                    data.append(create_data_row(check, group))

    except ObjectDoesNotExist:
        pass

    data = sorted(data, key=lambda k: (k["group"].lower(), k["skill_set_name"].lower()))
    return JsonResponse(data, safe=False)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_skill_set_details(
    request, character_pk: int, character: Character, skill_set_pk: int
) -> HttpResponse:

    skill_set = SkillSet.objects.get(id=skill_set_pk)
    skill_set_skills = SkillSetSkill.objects.filter(skill_set_id=skill_set_pk)

    out_data = list()

    url = (
        skill_set.ship_type.icon_url(ICON_SIZE_64, variant=EveType.IconVariant.REGULAR)
        if skill_set.ship_type
        else eveimageserver.type_icon_url(
            SKILL_SET_DEFAULT_ICON_TYPE_ID, size=ICON_SIZE_64
        )
    )

    for skill in skill_set_skills:
        cs = (
            character.skills.select_related("eve_type")
            .filter(eve_type_id=skill.eve_type_id)
            .first()
        )

        recommended_level_str = "-"
        required_level_str = "-"
        current_str = "-"
        result_icon = ICON_FAILED
        met_required = True

        if cs:
            current_str = MAP_ARABIC_TO_ROMAN_NUMBERS[cs.active_skill_level]

        if skill.recommended_level:
            recommended_level_str = MAP_ARABIC_TO_ROMAN_NUMBERS[skill.recommended_level]

        if skill.required_level:
            required_level_str = MAP_ARABIC_TO_ROMAN_NUMBERS[skill.required_level]

        if not cs:
            result_icon = ICON_FAILED
            met_required = False
        else:
            if (
                skill.required_level
                and not skill.recommended_level
                and cs.active_skill_level >= skill.required_level
            ):
                result_icon = ICON_FULL
            elif (
                skill.recommended_level
                and cs.active_skill_level >= skill.recommended_level
            ):
                result_icon = ICON_FULL
            elif skill.required_level and cs.active_skill_level >= skill.required_level:
                result_icon = ICON_PARTIAL
            else:
                met_required = False

        out_data.append(
            {
                "name": skill.eve_type.name,
                "required": required_level_str,
                "recommended": recommended_level_str,
                "current": current_str,
                "result_icon": result_icon,
                "met_required": met_required,
            }
        )

    met_all_required = True
    for data in out_data:
        if not data["met_required"]:
            met_all_required = False
            break

    out_data = sorted(out_data, key=lambda k: (k["name"].lower()))
    context = {
        "name": skill_set.name,
        "description": skill_set.description,
        "ship_url": url,
        "skills": out_data,
        "met_all_required": met_all_required,
        "icon_failed": ICON_FAILED,
        "icon_partial": ICON_PARTIAL,
        "icon_full": ICON_FULL,
        "icon_met_all_required": ICON_MET_ALL_REQUIRED,
    }

    return render(
        request,
        "memberaudit/modals/character_viewer/skill_set_content.html",
        context,
    )


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_skills_data(
    request, character_pk: int, character: Character
) -> JsonResponse:
    skills_data = list()
    try:
        for skill in character.skills.select_related(
            "eve_type", "eve_type__eve_group"
        ).filter(active_skill_level__gte=1):
            level_str = MAP_ARABIC_TO_ROMAN_NUMBERS[skill.active_skill_level]
            skill_name = f"{skill.eve_type.name} {level_str}"
            skills_data.append(
                {
                    "group": skill.eve_type.eve_group.name,
                    "skill": skill.eve_type.name,
                    "skill_name": f"{skill_name} - {skill.eve_type_id}",
                    "level": skill.active_skill_level,
                    "level_str": level_str,
                }
            )
    except ObjectDoesNotExist:
        pass

    return JsonResponse(skills_data, safe=False)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_wallet_journal_data(
    request, character_pk: int, character: Character
) -> JsonResponse:
    wallet_data = list()
    try:
        for row in character.wallet_journal.select_related(
            "first_party", "second_party"
        ).all():
            first_party = row.first_party.name if row.first_party else "-"
            second_party = row.second_party.name if row.second_party else "-"
            wallet_data.append(
                {
                    "date": row.date.isoformat(),
                    "ref_type": row.ref_type.replace("_", " ").title(),
                    "first_party": first_party,
                    "second_party": second_party,
                    "amount": float(row.amount),
                    "balance": float(row.balance),
                    "description": row.description,
                    "reason": row.reason,
                }
            )
    except ObjectDoesNotExist:
        pass
    return JsonResponse(wallet_data, safe=False)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_wallet_transactions_data(
    request, character_pk: int, character: Character
) -> JsonResponse:
    wallet_data = list()
    try:
        for row in character.wallet_transactions.select_related(
            "client", "eve_type", "location"
        ).all():
            buy_or_sell = gettext_lazy("Buy") if row.is_buy else gettext_lazy("Sell")
            wallet_data.append(
                {
                    "date": row.date.isoformat(),
                    "quantity": row.quantity,
                    "type": row.eve_type.name,
                    "unit_price": float(row.unit_price),
                    "total": float(
                        row.unit_price * row.quantity * (-1 if row.is_buy else 1)
                    ),
                    "client": row.client.name,
                    "location": row.location.name,
                    "is_buy": row.is_buy,
                    "buy_or_sell": buy_or_sell,
                }
            )
    except ObjectDoesNotExist:
        pass
    return JsonResponse(wallet_data, safe=False)
