from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Count, Q, F
from django.http import (
    JsonResponse,
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseForbidden,
)
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.timesince import timeuntil
from django.utils.html import format_html
from django.utils.timezone import now
from django.views.decorators.cache import cache_page

from bravado.exception import HTTPError
from esi.decorators import token_required

from allianceauth.authentication.models import CharacterOwnership, User
from allianceauth.eveonline.models import EveCharacter
from allianceauth.eveonline.evelinks import dotlan
from allianceauth.services.hooks import get_extension_logger

from . import tasks, __title__
from .decorators import fetch_character_if_allowed
from .helpers import eve_solar_system_to_html
from .models import Character, CharacterContract, CharacterMail
from .utils import (
    messages_plus,
    LoggerAddTag,
    create_link_html,
    DATETIME_FORMAT,
    create_fa_button_html,
)


logger = LoggerAddTag(get_extension_logger(__name__), __title__)


def create_img_html(src: str, classes: list) -> str:
    classes_str = 'class="{}"'.format(" ".join(classes)) if classes else ""
    return f'<img {classes_str}src="{str(src)}">'


def add_common_context(request, context: dict) -> dict:
    """adds the common context used by all view"""
    unregistered_count = Character.objects.unregistered_characters_of_user_count(
        request.user
    )
    registered_characters = list(
        Character.objects.select_related(
            "character_ownership", "character_ownership__character"
        )
        .filter(character_ownership__user=request.user)
        .order_by("character_ownership__character__character_name")
        .values("pk", name=F("character_ownership__character__character_name"))
    )
    new_context = {
        **{
            "app_title": __title__,
            "unregistered_count": unregistered_count,
            "registered_characters": registered_characters,
        },
        **context,
    }
    return new_context


@login_required
@permission_required("memberaudit.basic_access")
def index(request):
    return redirect("memberaudit:launcher")


#############################
# Section: Characters


@login_required
@permission_required("memberaudit.basic_access")
def launcher(request) -> HttpResponse:
    owned_chars_query = (
        CharacterOwnership.objects.filter(user=request.user)
        .select_related(
            "character",
            "memberaudit_character",
            "memberaudit_character__wallet_balance",
            "memberaudit_character__skillpoints",
            "memberaudit_character__unread_mail_count",
        )
        .order_by()
    )
    has_auth_characters = owned_chars_query.count() > 0
    auth_characters = list()
    unregistered_chars = list()
    for character_ownership in owned_chars_query:
        eve_character = character_ownership.character
        try:
            character = character_ownership.memberaudit_character
        except AttributeError:
            character = None
            unregistered_chars.append(eve_character.character_name)
        else:
            auth_characters.append(
                {
                    "character_id": eve_character.character_id,
                    "character_name": eve_character.character_name,
                    "character": character,
                    "alliance_id": eve_character.alliance_id,
                    "alliance_name": eve_character.alliance_name,
                    "corporation_id": eve_character.corporation_id,
                    "corporation_name": eve_character.corporation_name,
                }
            )

    context = {
        "page_title": "My Characters",
        "auth_characters": auth_characters,
        "has_auth_characters": has_auth_characters,
        "unregistered_chars": unregistered_chars,
        "has_registered_characters": len(auth_characters) > 0,
    }

    """
    if has_auth_characters:
        messages_plus.warning(
            request,
            format_html(
                "Please register all your characters. "
                "You currently have <strong>{}</strong> unregistered characters.",
                unregistered_chars,
            ),
        )
    """
    return render(
        request,
        "memberaudit/launcher.html",
        add_common_context(request, context),
    )


@login_required
@permission_required("memberaudit.basic_access")
@token_required(scopes=Character.get_esi_scopes())
def add_character(request, token) -> HttpResponse:
    token_char = EveCharacter.objects.get(character_id=token.character_id)
    try:
        character_ownership = CharacterOwnership.objects.select_related(
            "character"
        ).get(user=request.user, character=token_char)
    except CharacterOwnership.DoesNotExist:
        messages_plus.error(
            request,
            format_html(
                "You can register your main or alt characters."
                "However, character <strong>{}</strong> is neither. ",
                token_char.character_name,
            ),
        )
    else:
        with transaction.atomic():
            character, _ = Character.objects.update_or_create(
                character_ownership=character_ownership
            )

        tasks.update_character.delay(character_pk=character.pk)
        messages_plus.success(
            request,
            format_html(
                "<strong>{}</strong> has been registered. "
                "Note that it can take a minute until all character data is visible.",
                character.character_ownership.character,
            ),
        )

    return redirect("memberaudit:launcher")


@login_required
@permission_required("memberaudit.basic_access")
def remove_character(request, character_pk: int) -> HttpResponse:
    try:
        character = Character.objects.select_related(
            "character_ownership__user", "character_ownership__character"
        ).get(pk=character_pk)
    except Character.DoesNotExist:
        return HttpResponseNotFound(f"Character with pk {character_pk} not found")

    character_name = character.character_ownership.character.character_name
    if character.character_ownership.user == request.user:
        character.delete()
        messages_plus.success(
            request,
            format_html(
                "Removed character <strong>{}</strong> as requested.", character_name
            ),
        )
    else:
        return HttpResponseForbidden(
            f"No permission to remove Character with pk {character_pk}"
        )

    return redirect("memberaudit:launcher")


@login_required
@permission_required("memberaudit.basic_access")
def share_character(request, character_pk: int) -> HttpResponse:
    try:
        character = Character.objects.select_related(
            "character_ownership__user", "character_ownership__character"
        ).get(pk=character_pk)
    except Character.DoesNotExist:
        return HttpResponseNotFound(f"Character with pk {character_pk} not found")

    if character.character_ownership.user == request.user:
        character.is_shared = True
        character.save()
    else:
        return HttpResponseForbidden(
            f"No permission to remove Character with pk {character_pk}"
        )

    return redirect("memberaudit:launcher")


@login_required
@permission_required("memberaudit.basic_access")
def unshare_character(request, character_pk: int) -> HttpResponse:
    try:
        character = Character.objects.select_related(
            "character_ownership__user", "character_ownership__character"
        ).get(pk=character_pk)
    except Character.DoesNotExist:
        return HttpResponseNotFound(f"Character with pk {character_pk} not found")

    if character.character_ownership.user == request.user:
        character.is_shared = False
        character.save()
    else:
        return HttpResponseForbidden(
            f"No permission to remove Character with pk {character_pk}"
        )

    return redirect("memberaudit:launcher")


def _character_location_to_html(character: Character, category: str) -> str:
    """fetches current character location
    and returns either as solar system or location in HTML
    """
    try:
        solar_system, location = character.fetch_location()
    except HTTPError:
        logger.warning("Network error", exc_info=True)
        html = '<p class="text-danger">Network error</p>'
    except Exception as ex:
        logger.warning(f"Unexpected error: {ex}", exc_info=True)
        html = '<p class="text-danger">Unexpected error</p>'
    else:
        if category == "solar_system":
            html = eve_solar_system_to_html(solar_system)
        elif location:
            html = location.name
        else:
            html = "-"

    return html


@cache_page(30)
@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_solar_system_data(
    request, character_pk: int, character: Character
) -> HttpResponse:
    return HttpResponse(_character_location_to_html(character, "solar_system"))


@cache_page(30)
@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_location_data(
    request, character_pk: int, character: Character
) -> HttpResponse:
    return HttpResponse(_character_location_to_html(character, "location"))


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed(
    "details",
    "wallet_balance",
    "skillpoints",
    "character_ownership__user__profile__main_character",
)
def character_viewer(request, character_pk: int, character: Character):
    corporation_history = list()
    for entry in (
        character.corporation_history.exclude(is_deleted=True)
        .select_related("corporation")
        .order_by("start_date")
    ):
        if len(corporation_history) > 0:
            corporation_history[-1]["end_date"] = entry.start_date

        corporation_history.append(
            {
                "corporation_html": create_link_html(
                    dotlan.corporation_url(entry.corporation.name),
                    entry.corporation.name,
                ),
                "start_date": entry.start_date,
                "end_date": now(),
            }
        )

    try:
        character_details = character.details
    except ObjectDoesNotExist:
        character_details = None

    auth_character = character.character_ownership.character
    if character.character_ownership.user.profile.main_character:
        main_character = character.character_ownership.user.profile.main_character
        main = f"[{main_character.corporation_ticker}] {main_character.character_name}"
    else:
        main = "-"

    context = {
        "page_title": "Character Sheet",
        "character": character,
        "auth_character": auth_character,
        "character_details": character_details,
        "corporation_history": reversed(corporation_history),
        "main": main,
    }
    return render(
        request,
        "memberaudit/character_viewer.html",
        add_common_context(request, context),
    )


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

            if contract.contract_type == CharacterContract.TYPE_ITEM_EXCHANGE:
                if contract.items.count() > 1:
                    contract_description = "Multiple Items"
                else:
                    first_item = contract.items.first()
                    contract_description = (
                        first_item.eve_type.name if first_item else "?"
                    )
            elif contract.contract_type == CharacterContract.TYPE_COURIER:
                contract_description = (
                    f"{contract.start_location.eve_solar_system} >> "
                    f"{contract.end_location.eve_solar_system} "
                    f"({contract.volume:.0f} m3)"
                )
            else:
                contract_description = "(undefined)"

            data.append(
                {
                    "contract_id": contract.contract_id,
                    "contract": contract_description,
                    "type": contract.get_contract_type_display().title(),
                    "from": contract.issuer.name,
                    "to": contract.assignee.name if contract.assignee else "",
                    "status": contract.get_status_display(),
                    "date_issued": contract.date_issued.isoformat(),
                    "time_left": time_left,
                    "info": contract.title,
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
        for jump_clone in character.jump_clones.select_related(
            "location",
            "location__eve_solar_system",
            "location__eve_solar_system__eve_constellation__eve_region",
        ).all():
            if not jump_clone.location.is_empty:
                eve_solar_system = jump_clone.location.eve_solar_system
                solar_system = eve_solar_system_to_html(
                    eve_solar_system, show_region=False
                )
                region = eve_solar_system.eve_constellation.eve_region.name
            else:
                solar_system = "-"
                region = "-"

            implants = "<br>".join(
                sorted(
                    [
                        obj.eve_type.name
                        for obj in jump_clone.implants.select_related("eve_type")
                    ]
                )
            )
            if not implants:
                implants = "(none)"

            data.append(
                {
                    "jump_clone_id": jump_clone.jump_clone_id,
                    "region": region,
                    "solar_system": solar_system,
                    "location": jump_clone.location.name_plus,
                    "implants": implants,
                }
            )
    except ObjectDoesNotExist:
        pass

    return JsonResponse(data, safe=False)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_mail_headers_data(
    request, character_pk: int, character: Character
) -> HttpResponse:
    mails_data = list()
    try:
        for mail in character.mails.select_related(
            "from_entity", "from_mailing_list", "from_mailing_list"
        ).all():
            actions_html = (
                '<button type="button" class="btn btn-primary" '
                'data-toggle="modal" data-target="#modalCharacterMail" '
                f"data-character_pk={character_pk} data-mail_pk={mail.pk}>"
                '<i class="fas fa-search"></i></button>'
            )
            mails_data.append(
                {
                    "mail_id": mail.mail_id,
                    "labels": list(mail.labels.values_list("label_id", flat=True)),
                    "from": mail.from_entity.name,
                    "to": ", ".join(
                        sorted(
                            [
                                str(obj)
                                for obj in mail.recipients.select_related(
                                    "eve_entity", "mailing_list"
                                )
                            ]
                        )
                    ),
                    "subject": mail.subject,
                    "sent": mail.timestamp.strftime(DATETIME_FORMAT),
                    "action": actions_html,
                }
            )
    except ObjectDoesNotExist:
        pass

    return JsonResponse(mails_data, safe=False)


@login_required
@permission_required("memberaudit.basic_access")
@fetch_character_if_allowed()
def character_mail_data(
    request, character_pk: int, character: Character, mail_pk: int
) -> HttpResponse:
    try:
        mail = character.mails.get(pk=mail_pk)
    except CharacterMail.DoesNotExist:
        error_msg = f"Mail with pk {mail_pk} not found for character {character}"
        logger.warning(error_msg)
        return HttpResponseNotFound(error_msg)

    data = {
        "mail_id": mail.mail_id,
        "labels": list(mail.labels.values_list("label_id", flat=True)),
        "from": mail.from_entity.name,
        "to": ", ".join(
            sorted(
                [
                    str(obj)
                    for obj in mail.recipients.select_related(
                        "eve_entity", "mailing_list"
                    )
                ]
            )
        ),
        "subject": mail.subject,
        "sent": mail.timestamp.isoformat(),
        "body": mail.body_html if mail.body != "" else "(no data yet)",
    }
    return JsonResponse(data, safe=False)


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
        ).all():
            skills_data.append(
                {
                    "group": skill.eve_type.eve_group.name,
                    "skill": skill.eve_type.name,
                    "level": skill.trained_skill_level,
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
                    "amount": row.amount,
                    "balance": row.balance,
                    "description": row.description,
                }
            )
    except ObjectDoesNotExist:
        pass

    return JsonResponse(wallet_data, safe=False)


#############################
# Section: Analysis


@login_required
@permission_required("memberaudit.reports_access")
def reports(request) -> HttpResponse:
    context = {
        "page_title": "Reports",
    }
    return render(
        request,
        "memberaudit/reports.html",
        add_common_context(request, context),
    )


@login_required
@permission_required("memberaudit.reports_access")
def compliance_report_data(request) -> JsonResponse:
    if request.user.has_perm("memberaudit.view_everyhing"):
        users_qs = User.objects.all()
    else:
        users_qs = User.objects.none()
        if (
            request.user.has_perm("memberaudit.view_same_alliance")
            and request.user.profile.main_character.alliance_id
        ):
            users_qs = User.objects.select_related("profile__main_character").filter(
                profile__main_character__alliance_id=request.user.profile.main_character.alliance_id
            )
        elif request.user.has_perm("memberaudit.view_same_corporation"):
            users_qs = User.objects.select_related("profile__main_character").filter(
                profile__main_character__corporation_id=request.user.profile.main_character.corporation_id
            )

    member_users = (
        users_qs.filter(profile__state__name="Member")
        .annotate(total_chars=Count("character_ownerships"))
        .annotate(
            unregistered_chars=Count(
                "character_ownerships",
                filter=Q(character_ownerships__memberaudit_character=None),
            )
        )
        .select_related("profile__main_character")
    )

    user_data = list()
    for user in member_users:
        if user.profile.main_character:
            portrait_html = create_img_html(
                user.profile.main_character.portrait_url(), ["ra-avatar", "img-circle"]
            )
            main_character = user.profile.main_character
            user_data.append(
                {
                    "user_pk": user.pk,
                    "portrait": portrait_html,
                    "name": user.username,
                    "main": main_character.character_name,
                    "corporation": main_character.corporation_name,
                    "alliance": main_character.alliance_name,
                    "total_chars": user.total_chars,
                    "unregistered_chars": user.unregistered_chars,
                    "is_compliant": user.unregistered_chars == 0,
                    "compliance_str": "yes" if user.unregistered_chars == 0 else "no",
                }
            )

    return JsonResponse(user_data, safe=False)


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
    ):
        auth_character = character.character_ownership.character
        user_profile = character.character_ownership.user.profile
        portrait_html = create_img_html(
            auth_character.portrait_url(), ["ra-avatar", "img-circle"]
        )
        character_viewer_url = reverse(
            "memberaudit:character_viewer", args=[character.pk]
        )
        actions_html = create_fa_button_html(
            url=character_viewer_url,
            fa_code="fas fa-search",
            button_type="primary",
        )
        alliance_name = (
            auth_character.alliance_name if auth_character.alliance_name else "-"
        )
        character_link = create_link_html(
            character_viewer_url, auth_character.character_name, new_window=False
        )
        character_list.append(
            {
                "character_pk": character.pk,
                "portrait": portrait_html,
                "character_name": character_link,
                "corporation_name": auth_character.corporation_name,
                "alliance_name": alliance_name,
                "main_name": user_profile.main_character.character_name,
                "state_name": user_profile.state.name,
                "actions": actions_html,
            }
        )
    return JsonResponse(character_list, safe=False)
