import datetime as dt
from typing import Optional, Tuple

import humanize

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Count, F, Max, Q, Sum
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timesince import timeuntil
from django.utils.timezone import now
from django.utils.translation import gettext, gettext_lazy
from eveuniverse.core import dotlan, eveimageserver
from eveuniverse.models import EveSolarSystem, EveType

from allianceauth.eveonline.models import EveCharacter
from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag
from app_utils.views import (
    bootstrap_icon_plus_name_html,
    bootstrap_label_html,
    fontawesome_link_button_html,
    link_html,
    no_wrap_html,
    yesno_str,
    yesnonone_str,
)

from .. import __title__
from ..constants import (
    DATETIME_FORMAT,
    DEFAULT_ICON_SIZE,
    MAP_ARABIC_TO_ROMAN_NUMBERS,
    MY_DATETIME_FORMAT,
    SKILL_SET_DEFAULT_ICON_TYPE_ID,
    EveCategoryId,
)
from ..decorators import fetch_character_if_allowed
from ..models import (
    Character,
    CharacterAsset,
    CharacterContract,
    CharacterContractItem,
    CharacterMail,
    Location,
    SkillSet,
    SkillSetSkill,
)
from .helpers import UNGROUPED_SKILL_SET, add_common_context

# module constants

MAIL_LABEL_ID_ALL_MAILS = 0

ICON_SIZE_64 = 64
CHARACTER_VIEWER_DEFAULT_TAB = "mails"
ICON_FAILED = "fas fa-times boolean-icon-false"
ICON_PARTIAL = "fas fa-check text-warning"
ICON_FULL = "fas fa-check-double text-success"
ICON_MET_ALL_REQUIRED = "fas fa-check text-success"

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


def eve_solar_system_to_html(solar_system: EveSolarSystem, show_region=True) -> str:
    if solar_system.is_high_sec:
        css_class = "text-high-sec"
    elif solar_system.is_low_sec:
        css_class = "text-low-sec"
    else:
        css_class = "text-null-sec"

    region_html = (
        f" / {solar_system.eve_constellation.eve_region.name}" if show_region else ""
    )
    return format_html(
        '{} <span class="{}">{}</span>{}',
        link_html(dotlan.solar_system_url(solar_system.name), solar_system.name),
        css_class,
        round(solar_system.security_status, 1),
        region_html,
    )


def item_icon_plus_name_html(item, size=DEFAULT_ICON_SIZE) -> Tuple[str, str]:
    """returns generated HTML with name and icon for asset and contract items"""
    if item.is_blueprint_copy:
        variant = item.eve_type.IconVariant.BPC
    else:
        variant = None

    name = item.name_display
    name_html = bootstrap_icon_plus_name_html(
        icon_url=item.eve_type.icon_url(size=DEFAULT_ICON_SIZE, variant=variant),
        name=name,
        size=size,
    )
    return name_html, name


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed(
    "details",
    "wallet_balance",
    "skillpoints",
    "character_ownership__user",
    "character_ownership__user__profile__main_character",
    "character_ownership__character",
    "location__location",
    "location__eve_solar_system",
    "location__eve_solar_system__eve_constellation__eve_region",
    "online_status",
)
def character_viewer(request, character_pk: int, character: Character) -> HttpResponse:
    """main view for showing a character with all details

    Args:
    - character_pk: PK for character to be shown

    GET Params:
    - tab: ID of tab to be shown  (optional)
    """
    # character details
    try:
        character_details = character.details
    except ObjectDoesNotExist:
        character_details = None

    # main character
    auth_character = character.character_ownership.character
    try:
        main_character = character.character_ownership.user.profile.main_character
        main = f"[{main_character.corporation_ticker}] {main_character.character_name}"
    except AttributeError:
        main_character = None
        main = "-"

    # mailing lists
    mailing_lists_qs = character.mailing_lists.all().annotate(
        unread_count=Count("recipient_mails", filter=Q(recipient_mails__is_read=False))
    )
    mailing_lists = [
        {
            "list_id": obj.id,
            "name_plus": obj.name_plus,
            "unread_count": obj.unread_count,
        }
        for obj in mailing_lists_qs
    ]

    # mail labels
    mail_labels = list(
        character.mail_labels.values(
            "label_id", "name", unread_count_2=F("unread_count")
        )
    )
    total_unread_count = sum(
        [obj["unread_count_2"] for obj in mail_labels if obj["unread_count_2"]]
    )
    total_unread_count += sum(
        [obj["unread_count"] for obj in mailing_lists if obj["unread_count"]]
    )
    mail_labels.append(
        {
            "label_id": MAIL_LABEL_ID_ALL_MAILS,
            "name": "All Mails",
            "unread_count_2": total_unread_count,
        }
    )

    # list of all characters owned by this user for sidebar
    accessible_characters = set(
        Character.objects.user_has_access(user=request.user).values_list(
            "pk", flat=True
        )
    )
    all_characters = (
        EveCharacter.objects.select_related(
            "character_ownership__memberaudit_character"
        )
        .filter(character_ownership__user=character.character_ownership.user)
        .order_by("character_name")
        .annotate(
            memberaudit_character_pk=F("character_ownership__memberaudit_character")
        )
        .annotate(is_shared=F("character_ownership__memberaudit_character__is_shared"))
        .values(
            "character_id", "character_name", "memberaudit_character_pk", "is_shared"
        )
    )
    all_characters = [
        {
            **obj,
            **{
                "has_access": (obj["memberaudit_character_pk"] in accessible_characters)
            },
        }
        for obj in all_characters
    ]

    # assets total value
    character_assets_total = (
        character.assets.exclude(is_blueprint_copy=True)
        .aggregate(
            total=Sum(
                F("quantity") * F("eve_type__market_price__average_price"),
                output_field=models.FloatField(),
            )
        )
        .get("total")
    )

    # implants
    try:
        has_implants = character.implants.count() > 0
    except ObjectDoesNotExist:
        has_implants = False

    # last updates
    try:
        last_updates = {
            obj["section"]: obj["finished_at"]
            for obj in character.update_status_set.filter(is_success=True).values(
                "section", "finished_at"
            )
        }
    except ObjectDoesNotExist:
        last_updates = None

    page_title = "Character Sheet"
    if not character.user_is_owner(request.user):
        page_title = format_html(
            '{}&nbsp;<i class="far fa-eye" title="You do not own this character"></i>',
            page_title,
        )

    context = {
        "page_title": page_title,
        "character": character,
        "auth_character": auth_character,
        "character_details": character_details,
        "mail_labels": mail_labels,
        "mailing_lists": mailing_lists,
        "main": main,
        "main_character_id": main_character.character_id if main_character else None,
        "all_characters": all_characters,
        "show_tab": request.GET.get("tab", ""),
        "last_updates": last_updates,
        "character_assets_total": character_assets_total,
        "has_implants": has_implants,
        "is_assets_updating": character.is_section_updating(
            Character.UpdateSection.ASSETS
        ),
    }
    return render(
        request,
        "memberaudit/character_viewer.html",
        add_common_context(request, context),
    )


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_assets_data(
    request, character_pk: int, character: Character
) -> JsonResponse:
    data = list()
    try:
        asset_qs = (
            character.assets.annotate_pricing()
            .select_related(
                "eve_type",
                "eve_type__eve_group",
                "eve_type__eve_group__eve_category",
                "location__eve_solar_system",
                "location__eve_solar_system__eve_constellation__eve_region",
            )
            .filter(location__isnull=False)
        )
    except ObjectDoesNotExist:
        return HttpResponseNotFound()

    assets_with_children_ids = set(
        character.assets.filter(children__isnull=False).values_list(
            "item_id", flat=True
        )
    )
    location_counts = {
        obj["id"]: obj["items_count"]
        for obj in (
            Location.objects.select_related("characterasset__character")
            .filter(characterasset__character=character)
            .annotate(items_count=Count("characterasset"))
            .values("id", "items_count")
        )
    }
    for asset in asset_qs:
        if asset.location.eve_solar_system:
            region = asset.location.eve_solar_system.eve_constellation.eve_region.name
            solar_system = asset.location.eve_solar_system.name
        else:
            region = ""
            solar_system = ""

        is_ship = yesno_str(
            asset.eve_type.eve_group.eve_category_id == EveCategoryId.SHIP
        )

        if asset.item_id in assets_with_children_ids:
            ajax_children_url = reverse(
                "memberaudit:character_asset_container",
                args=[character.pk, asset.pk],
            )
            actions_html = (
                '<button type="button" class="btn btn-default btn-sm" '
                'data-toggle="modal" data-target="#modalCharacterAssetContainer" '
                f"data-ajax_children_url={ajax_children_url}>"
                '<i class="fas fa-search"></i></button>'
            )
        else:
            actions_html = ""

        location_name = (
            f"{asset.location.name_plus} ({location_counts.get(asset.location_id, 0)})"
        )
        name_html, name = item_icon_plus_name_html(asset)
        data.append(
            {
                "item_id": asset.item_id,
                "location": location_name,
                "name": {"display": name_html, "sort": name},
                "quantity": asset.quantity if not asset.is_singleton else "",
                "group": asset.group_display,
                "volume": asset.eve_type.volume,
                "price": asset.price,
                "total": asset.total,
                "actions": actions_html,
                "region": region,
                "solar_system": solar_system,
                "is_ship": is_ship,
            }
        )

    return JsonResponse(data, safe=False)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_asset_container(
    request, character_pk: int, character: Character, parent_asset_pk: int
) -> HttpResponse:
    try:
        parent_asset = character.assets.select_related(
            "location", "eve_type", "eve_type__eve_group"
        ).get(pk=parent_asset_pk)
    except CharacterAsset.DoesNotExist:
        error_msg = (
            f"Asset with pk {parent_asset_pk} not found for character {character}"
        )
        logger.warning(error_msg)
        context = {
            "error": error_msg,
        }
    else:
        context = {
            "character": character,
            "parent_asset": parent_asset,
            "parent_asset_icon_url": parent_asset.eve_type.icon_url(
                size=DEFAULT_ICON_SIZE
            ),
        }
    return render(
        request,
        "memberaudit/modals/character_viewer/asset_container_content.html",
        context,
    )


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_asset_container_data(
    request, character_pk: int, character: Character, parent_asset_pk: int
) -> JsonResponse:
    data = list()
    try:
        parent_asset = character.assets.get(pk=parent_asset_pk)
    except CharacterAsset.DoesNotExist:
        error_msg = (
            f"Asset with pk {parent_asset_pk} not found for character {character}"
        )
        logger.warning(error_msg)
        return HttpResponseNotFound(error_msg)

    try:
        assets_qs = parent_asset.children.annotate_pricing().select_related(
            "eve_type",
            "eve_type__eve_group",
            "eve_type__eve_group__eve_category",
        )
    except ObjectDoesNotExist:
        return HttpResponseNotFound()

    for asset in assets_qs:
        name_html, name = item_icon_plus_name_html(asset)
        data.append(
            {
                "item_id": asset.item_id,
                "name": {"display": name_html, "sort": name},
                "quantity": asset.quantity if not asset.is_singleton else "",
                "group": asset.group_display,
                "volume": asset.eve_type.volume,
                "price": asset.price,
                "total": asset.total,
            }
        )

    return JsonResponse(data, safe=False)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_contacts_data(
    request, character_pk: int, character: Character
) -> JsonResponse:
    data = list()
    try:
        for contact in character.contacts.select_related("eve_entity").all():
            is_watched = contact.is_watched is True
            is_blocked = contact.is_blocked is True
            name = contact.eve_entity.name
            is_npc = contact.eve_entity.is_npc
            if is_npc:
                name_plus = format_html(
                    "{} {}", name, bootstrap_label_html("NPC", "info")
                )
            else:
                name_plus = name

            name_html = bootstrap_icon_plus_name_html(
                contact.eve_entity.icon_url(DEFAULT_ICON_SIZE), name_plus, avatar=True
            )
            data.append(
                {
                    "id": contact.eve_entity_id,
                    "name": {"display": name_html, "sort": name},
                    "standing": contact.standing,
                    "type": contact.eve_entity.get_category_display().title(),
                    "is_watched": is_watched,
                    "is_blocked": is_blocked,
                    "is_watched_str": yesno_str(is_watched),
                    "is_blocked_str": yesno_str(is_blocked),
                    "is_npc_str": yesno_str(is_npc),
                    "level": contact.standing_level.title(),
                }
            )
    except ObjectDoesNotExist:
        pass

    return JsonResponse(data, safe=False)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_contracts_data(
    request, character_pk: int, character: Character
) -> JsonResponse:
    data = list()
    try:
        for contract in character.contracts.select_related("issuer", "assignee").all():
            if now() < contract.date_expired:
                time_left = timeuntil(contract.date_expired, now())
            else:
                time_left = "expired"

            ajax_contract_detail = reverse(
                "memberaudit:character_contract_details",
                args=[character.pk, contract.pk],
            )

            actions_html = (
                '<button type="button" class="btn btn-primary" '
                'data-toggle="modal" data-target="#modalCharacterContract" '
                f"data-ajax_contract_detail={ajax_contract_detail}>"
                '<i class="fas fa-search"></i></button>'
            )
            data.append(
                {
                    "contract_id": contract.contract_id,
                    "summary": contract.summary(),
                    "type": contract.get_contract_type_display().title(),
                    "from": contract.issuer.name,
                    "to": contract.assignee.name if contract.assignee else "(None)",
                    "status": contract.get_status_display(),
                    "date_issued": contract.date_issued.isoformat(),
                    "time_left": time_left,
                    "info": contract.title,
                    "actions": actions_html,
                }
            )
    except ObjectDoesNotExist:
        pass

    return JsonResponse(data, safe=False)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_contract_details(
    request, character_pk: int, character: Character, contract_pk: int
) -> HttpResponse:
    error_msg = None
    try:
        contract = (
            character.contracts.select_related(
                "issuer", "start_location", "end_location", "assignee"
            )
            .prefetch_related("bids")
            .get(pk=contract_pk)
        )
    except CharacterContract.DoesNotExist:
        error_msg = (
            f"Contract with pk {contract_pk} not found for character {character}"
        )
        logger.warning(error_msg)
        context = {
            "error": error_msg,
            "character": character,
        }
    else:
        try:
            has_items_included = contract.items.filter(is_included=True).exists()
            has_items_requested = contract.items.filter(is_included=False).exists()
        except ObjectDoesNotExist:
            has_items_included = False
            has_items_requested = False

        try:
            current_bid = (
                contract.bids.all().aggregate(Max("amount")).get("amount__max")
            )
            bids_count = contract.bids.count()
        except ObjectDoesNotExist:
            current_bid = None
            bids_count = None

        context = {
            "character": character,
            "contract": contract,
            "contract_summary": contract.summary(),
            "MY_DATETIME_FORMAT": MY_DATETIME_FORMAT,
            "has_items_included": has_items_included,
            "has_items_requested": has_items_requested,
            "current_bid": current_bid,
            "bids_count": bids_count,
        }
    return render(
        request,
        "memberaudit/modals/character_viewer/contract_content.html",
        add_common_context(request, context),
    )


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_contract_items_included_data(
    request, character_pk: int, character: Character, contract_pk: int
) -> JsonResponse:
    return _character_contract_items_data(
        request=request,
        character_pk=character_pk,
        character=character,
        contract_pk=contract_pk,
        is_included=True,
    )


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_contract_items_requested_data(
    request, character_pk: int, character: Character, contract_pk: int
) -> JsonResponse:
    return _character_contract_items_data(
        request=request,
        character_pk=character_pk,
        character=character,
        contract_pk=contract_pk,
        is_included=False,
    )


def _character_contract_items_data(
    request,
    character_pk: int,
    character: Character,
    contract_pk: int,
    is_included: bool,
) -> JsonResponse:
    data = list()
    try:
        contract = character.contracts.prefetch_related("items").get(pk=contract_pk)
    except CharacterAsset.DoesNotExist:
        error_msg = (
            f"Contract with pk {contract_pk} not found for character {character}"
        )
        logger.warning(error_msg)
        return HttpResponseNotFound(error_msg)

    try:
        items_qs = (
            contract.items.annotate_pricing()
            .filter(is_included=is_included)
            .select_related(
                "eve_type",
                "eve_type__eve_group",
                "eve_type__eve_group__eve_category",
            )
        )
    except ObjectDoesNotExist:
        items_qs = CharacterContractItem.objects.none()

    for item in items_qs:
        name_html, name = item_icon_plus_name_html(item)
        data.append(
            {
                "id": item.record_id,
                "name": {
                    "display": name_html,
                    "sort": name,
                },
                "quantity": item.quantity if not item.is_singleton else "",
                "group": item.eve_type.eve_group.name,
                "category": item.eve_type.eve_group.eve_category.name,
                "price": item.price,
                "total": item.total,
                "is_blueprint_copy": item.is_blueprint_copy,
            }
        )

    return JsonResponse(data, safe=False)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_corporation_history(
    request, character_pk: int, character: Character
) -> HttpResponse:
    corporation_history = list()
    try:
        corporation_history_qs = character.corporation_history.select_related(
            "corporation"
        ).order_by("start_date")
    except ObjectDoesNotExist:
        pass

    else:
        for entry in corporation_history_qs:
            if len(corporation_history) > 0:
                corporation_history[-1]["end_date"] = entry.start_date
                corporation_history[-1]["is_last"] = False

            corporation_history.append(
                {
                    "id": entry.pk,
                    "corporation_name": entry.corporation.name,
                    "start_date": entry.start_date,
                    "end_date": now(),
                    "is_last": True,
                    "is_deleted": entry.is_deleted,
                }
            )

    context = {
        "corporation_history": reversed(corporation_history),
        "has_corporation_history": len(corporation_history) > 0,
    }
    return render(
        request,
        "memberaudit/partials/character_viewer/tabs/corporation_history_2.html",
        add_common_context(request, context),
    )


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_implants_data(
    request, character_pk: int, character: Character
) -> JsonResponse:
    data = list()
    try:
        for implant in character.implants.select_related("eve_type").prefetch_related(
            "eve_type__dogma_attributes"
        ):
            implant_html = bootstrap_icon_plus_name_html(
                implant.eve_type.icon_url(
                    DEFAULT_ICON_SIZE, variant=EveType.IconVariant.REGULAR
                ),
                implant.eve_type.name,
            )
            try:
                slot_num = int(
                    implant.eve_type.dogma_attributes.get(
                        eve_dogma_attribute_id=331
                    ).value
                )
            except (ObjectDoesNotExist, AttributeError):
                slot_num = 0

            data.append(
                {
                    "id": implant.pk,
                    "implant": {"display": implant_html, "sort": slot_num},
                }
            )
    except ObjectDoesNotExist:
        pass

    return JsonResponse(data, safe=False)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_loyalty_data(
    request, character_pk: int, character: Character
) -> JsonResponse:
    data = list()
    try:
        for entry in character.loyalty_entries.select_related("corporation"):
            corporation_html = bootstrap_icon_plus_name_html(
                entry.corporation.icon_url(DEFAULT_ICON_SIZE), entry.corporation.name
            )
            data.append(
                {
                    "id": entry.pk,
                    "corporation": {
                        "display": corporation_html,
                        "sort": entry.corporation.name,
                    },
                    "loyalty_points": entry.loyalty_points,
                }
            )
    except ObjectDoesNotExist:
        pass

    return JsonResponse(data, safe=False)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_jump_clones_data(
    request, character_pk: int, character: Character
) -> HttpResponse:
    data = list()
    try:
        for jump_clone in (
            character.jump_clones.select_related(
                "location",
                "location__eve_solar_system",
                "location__eve_solar_system__eve_constellation__eve_region",
            )
            .prefetch_related("implants", "implants__eve_type__dogma_attributes")
            .all()
        ):
            if not jump_clone.location.is_empty:
                eve_solar_system = jump_clone.location.eve_solar_system
                solar_system = eve_solar_system_to_html(
                    eve_solar_system, show_region=False
                )
                region = eve_solar_system.eve_constellation.eve_region.name
            else:
                solar_system = "-"
                region = "-"

            implants_data = list()
            for obj in jump_clone.implants.all():
                dogma_attributes = {
                    attribute.eve_dogma_attribute_id: attribute.value
                    for attribute in obj.eve_type.dogma_attributes.all()
                }
                try:
                    slot_num = int(dogma_attributes[331])
                except (KeyError, TypeError):
                    slot_num = 0

                implants_data.append(
                    {
                        "name": obj.eve_type.name,
                        "icon_url": obj.eve_type.icon_url(
                            DEFAULT_ICON_SIZE, variant=EveType.IconVariant.REGULAR
                        ),
                        "slot_num": slot_num,
                    }
                )
            if implants_data:
                implants = "<br>".join(
                    bootstrap_icon_plus_name_html(
                        x["icon_url"], no_wrap_html(x["name"]), size=24
                    )
                    for x in sorted(implants_data, key=lambda k: k["slot_num"])
                )
            else:
                implants = "(none)"

            data.append(
                {
                    "id": jump_clone.pk,
                    "region": region,
                    "solar_system": solar_system,
                    "location": jump_clone.location.name_plus,
                    "implants": implants,
                }
            )
    except ObjectDoesNotExist:
        pass

    return JsonResponse(data, safe=False)


def _character_mail_headers_data(request, character, mail_headers_qs) -> JsonResponse:
    mails_data = list()
    try:
        for mail in mail_headers_qs.select_related("sender").prefetch_related(
            "recipients"
        ):
            mail_ajax_url = reverse(
                "memberaudit:character_mail", args=[character.pk, mail.pk]
            )
            if mail.body:
                actions_html = (
                    '<button type="button" class="btn btn-primary" '
                    'data-toggle="modal" data-target="#modalCharacterMail" '
                    f"data-ajax_url={mail_ajax_url}>"
                    '<i class="fas fa-search"></i></button>'
                )
            else:
                actions_html = ""

            mails_data.append(
                {
                    "mail_id": mail.mail_id,
                    "from": mail.sender.name_plus,
                    "to": ", ".join(
                        sorted([obj.name_plus for obj in mail.recipients.all()])
                    ),
                    "subject": mail.subject,
                    "sent": mail.timestamp.isoformat(),
                    "action": actions_html,
                    "is_read": mail.is_read,
                    "is_unread_str": yesno_str(mail.is_read is False),
                }
            )
    except ObjectDoesNotExist:
        pass

    return JsonResponse(mails_data, safe=False)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_mail_headers_by_label_data(
    request, character_pk: int, character: Character, label_id: int
) -> JsonResponse:
    if label_id == MAIL_LABEL_ID_ALL_MAILS:
        mail_headers_qs = character.mails.all()
    else:
        mail_headers_qs = character.mails.filter(labels__label_id=label_id)

    return _character_mail_headers_data(request, character, mail_headers_qs)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_mail_headers_by_list_data(
    request, character_pk: int, character: Character, list_id: int
) -> JsonResponse:
    mail_headers_qs = character.mails.filter(recipients__id=list_id)
    return _character_mail_headers_data(request, character, mail_headers_qs)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_mail(
    request, character_pk: int, character: Character, mail_pk: int
) -> JsonResponse:
    try:
        mail = (
            character.mails.select_related("sender")
            .prefetch_related("recipients")
            .get(pk=mail_pk)
        )
    except CharacterMail.DoesNotExist:
        error_msg = f"Mail with pk {mail_pk} not found for character {character}"
        logger.warning(error_msg)
        return HttpResponseNotFound(error_msg)
    recipients = sorted(
        [
            {
                "name": obj.name_plus,
                "link": link_html(obj.external_url(), obj.name_plus),
            }
            for obj in mail.recipients.all()
        ],
        key=lambda k: k["name"],
    )
    context = {
        "mail_id": mail.mail_id,
        "labels": list(mail.labels.values_list("label_id", flat=True)),
        "sender": link_html(mail.sender.external_url(), mail.sender.name_plus),
        "recipients": format_html(", ".join([obj["link"] for obj in recipients])),
        "subject": mail.subject,
        "timestamp": mail.timestamp,
        "body": mail.body_html if mail.body else None,
        "MY_DATETIME_FORMAT": MY_DATETIME_FORMAT,
    }
    return render(
        request, "memberaudit/modals/character_viewer/mail_content.html", context
    )


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
def character_attribute_data(
    request, character_pk: int, character: Character
) -> HttpResponse:

    try:
        character_attributes = character.attributes
    except ObjectDoesNotExist:
        character_attributes = None

    context = {"character_attributes": character_attributes}

    return render(
        request,
        "memberaudit/partials/character_viewer/tabs/character_attributes_content.html",
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


#############################
# Section: Character Finder


@login_required
@permission_required("memberaudit.finder_access")
def character_finder(request) -> HttpResponse:
    context = {
        "page_title": "Character Finder",
    }
    return render(
        request,
        "memberaudit/character_finder.html",
        add_common_context(request, context),
    )


@login_required
@permission_required("memberaudit.finder_access")
def character_finder_data(request) -> JsonResponse:
    character_list = list()
    for character in Character.objects.user_has_access(
        user=request.user
    ).select_related(
        "character_ownership__character",
        "character_ownership__user",
        "character_ownership__user__profile__main_character",
        "character_ownership__user__profile__state",
        "location__location",
        "location__eve_solar_system",
        "location__eve_solar_system__eve_constellation__eve_region",
    ):
        auth_character = character.character_ownership.character
        character_viewer_url = reverse(
            "memberaudit:character_viewer", args=[character.pk]
        )
        actions_html = fontawesome_link_button_html(
            url=character_viewer_url,
            fa_code="fas fa-search",
            button_type="primary",
        )
        alliance_name = (
            auth_character.alliance_name if auth_character.alliance_name else ""
        )
        character_organization = format_html(
            "{}<br><em>{}</em>", auth_character.corporation_name, alliance_name
        )
        user_profile = character.character_ownership.user.profile
        try:
            main_html = bootstrap_icon_plus_name_html(
                user_profile.main_character.portrait_url(),
                user_profile.main_character.character_name,
                avatar=True,
            )
            main_corporation = user_profile.main_character.corporation_name
            main_alliance = (
                user_profile.main_character.alliance_name
                if user_profile.main_character.alliance_name
                else ""
            )
            main_organization = format_html(
                "{}<br><em>{}</em>", auth_character.corporation_name, alliance_name
            )

        except AttributeError:
            main_alliance = main_organization = main_corporation = main_html = ""

        text = format_html(
            "{}&nbsp;{}",
            mark_safe('&nbsp;<i class="fas fa-crown" title="Main character">')
            if character.is_main
            else "",
            mark_safe('&nbsp;<i class="far fa-eye" title="Shared character">')
            if character.is_shared
            else "",
        )
        character_html = bootstrap_icon_plus_name_html(
            auth_character.portrait_url(),
            auth_character.character_name,
            avatar=True,
            url=character_viewer_url,
            text=text,
        )

        try:
            location_name = (
                character.location.location.name if character.location.location else ""
            )
            solar_system_html = eve_solar_system_to_html(
                character.location.eve_solar_system
            )
            location_html = format_html("{}<br>{}", location_name, solar_system_html)
            solar_system_name = character.location.eve_solar_system.name
            region_name = (
                character.location.eve_solar_system.eve_constellation.eve_region.name
            )
        except ObjectDoesNotExist:
            location_html = ""
            solar_system_name = ""
            region_name = ""

        alliance_name = (
            auth_character.alliance_name if auth_character.alliance_name else ""
        )
        character_list.append(
            {
                "character_pk": character.pk,
                "character": {
                    "display": character_html,
                    "sort": auth_character.character_name,
                },
                "character_organization": character_organization,
                "main_character": main_html,
                "main_organization": main_organization,
                "state_name": user_profile.state.name,
                "location": location_html,
                "actions": actions_html,
                "alliance_name": alliance_name,
                "corporation_name": auth_character.corporation_name,
                "solar_system_name": solar_system_name,
                "region_name": region_name,
                "main_alliance_name": main_alliance,
                "main_corporation_name": main_corporation,
                "main_str": yesno_str(character.is_main),
            }
        )
    return JsonResponse(character_list, safe=False)
