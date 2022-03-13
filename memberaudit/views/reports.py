from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html
from eveuniverse.core import eveimageserver
from eveuniverse.models import EveType

from allianceauth.authentication.models import get_guest_state_pk
from allianceauth.eveonline.models import EveCharacter
from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag
from app_utils.views import bootstrap_icon_plus_name_html, yesno_str

from .. import __title__
from ..constants import DEFAULT_ICON_SIZE, SKILL_SET_DEFAULT_ICON_TYPE_ID
from ..models import Character, General, SkillSetGroup
from .helpers import UNGROUPED_SKILL_SET, add_common_context

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


def create_main_organization_html(main_character) -> str:
    return format_html(
        "{}{}",
        main_character.corporation_name,
        f" [{main_character.alliance_ticker}]" if main_character.alliance_name else "",
    )


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
def user_compliance_report_data(request) -> JsonResponse:
    users_and_character_counts = (
        General.accessible_users(request.user)
        .exclude(profile__state__pk=get_guest_state_pk())
        .annotate(total_chars=Count("character_ownerships__character", distinct=True))
        .annotate(
            unregistered_chars=Count(
                "character_ownerships",
                filter=Q(character_ownerships__memberaudit_character=None),
                distinct=True,
            )
        )
        .select_related("profile__main_character", "profile__state")
    )
    user_data = list()
    for user in users_and_character_counts:
        if user.profile.main_character:
            main_character = user.profile.main_character
            if user == request.user or request.user.has_perm(
                "memberaudit.characters_access"
            ):
                try:
                    character = main_character.character_ownership.memberaudit_character
                except ObjectDoesNotExist:
                    url = None
                else:
                    url = reverse("memberaudit:character_viewer", args=[character.pk])
            else:
                url = None
            main_name = main_character.character_name
            main_html = bootstrap_icon_plus_name_html(
                main_character.portrait_url(),
                main_character.character_name,
                avatar=True,
                url=url,
            )
            corporation_name = main_character.corporation_name
            organization_html = create_main_organization_html(main_character)
            alliance_name = (
                main_character.alliance_name if main_character.alliance_name else ""
            )
            is_compliant = user.unregistered_chars == 0
        else:
            main_name = user.username
            main_html = bootstrap_icon_plus_name_html(
                eveimageserver.character_portrait_url(1, size=DEFAULT_ICON_SIZE),
                main_name,
                avatar=True,
                url=url,
            )
            alliance_name = organization_html = corporation_name = ""
            is_compliant = False

        is_registered = user.unregistered_chars < user.total_chars
        user_data.append(
            {
                "id": user.pk,
                "main": {
                    "display": main_html,
                    "sort": main_name,
                },
                "organization": {
                    "display": organization_html,
                    "sort": corporation_name,
                },
                "state": user.profile.state.name,
                "corporation_name": corporation_name,
                "alliance_name": alliance_name,
                "total_chars": user.total_chars,
                "unregistered_chars": user.unregistered_chars,
                "is_registered": is_registered,
                "registered_str": yesno_str(is_registered),
                "is_compliant": is_compliant,
                "compliance_str": yesno_str(is_compliant),
            }
        )
    return JsonResponse(user_data, safe=False)


@login_required
@permission_required("memberaudit.reports_access")
def corporation_compliance_report_data(request) -> JsonResponse:
    relevant_user_ids = list(
        General.accessible_users(request.user)
        .exclude(profile__state__pk=get_guest_state_pk())
        .values_list("id", flat=True)
    )
    corporations = (
        EveCharacter.objects.select_related(
            "userprofile",
            "userprofile__user__character_ownerships__character",
            "userprofile__user__character_ownerships",
        )
        .filter(userprofile__in=relevant_user_ids)
        .values(
            "corporation_id",
            "corporation_name",
            "alliance_id",
            "alliance_name",
            "alliance_ticker",
        )
        .distinct()
        .annotate(mains_count=Count("userprofile", distinct=True))
        .annotate(
            characters_count=Count(
                "userprofile__user__character_ownerships__character", distinct=True
            )
        )
        .annotate(
            unregistered_count=Count(
                "userprofile__user__character_ownerships",
                filter=Q(
                    userprofile__user__character_ownerships__memberaudit_character__isnull=True
                ),
                distinct=True,
            )
        )
    )
    data = list()
    for corporation in corporations:
        organization_name = "{}{}".format(
            corporation["corporation_name"],
            f" [{corporation['alliance_ticker']}]"
            if corporation["alliance_ticker"]
            else "",
        )
        alliance_name = (
            corporation["alliance_name"] if corporation["alliance_name"] else ""
        )
        compliance_p = (
            round(
                (corporation["characters_count"] - corporation["unregistered_count"])
                / corporation["characters_count"]
                * 100
            )
            if corporation["characters_count"] > 0
            else 0
        )
        is_compliant = compliance_p == 100
        data.append(
            {
                "id": corporation["corporation_id"],
                "organization_html": {
                    "display": bootstrap_icon_plus_name_html(
                        icon_url=eveimageserver.corporation_logo_url(
                            corporation_id=corporation["corporation_id"],
                            size=DEFAULT_ICON_SIZE,
                        ),
                        name=organization_name,
                    ),
                    "sort": corporation["corporation_name"],
                },
                "corporation_name": corporation["corporation_name"],
                "alliance_name": alliance_name,
                "mains_count": corporation["mains_count"],
                "characters_count": corporation["characters_count"],
                "unregistered_count": corporation["unregistered_count"],
                "compliance_percent": compliance_p,
                "is_compliant": is_compliant,
                "is_partly_compliant": compliance_p >= 85,
                "is_compliant_str": yesno_str(is_compliant),
            }
        )
    return JsonResponse(data, safe=False)


@login_required
@permission_required("memberaudit.reports_access")
def skill_sets_report_data(request) -> JsonResponse:
    def create_data_row(group, character) -> dict:
        user = character.character_ownership.user
        auth_character = character.character_ownership.character
        main_character = user.profile.main_character
        if main_character:
            main_name = main_character.character_name
            main_html = bootstrap_icon_plus_name_html(
                user.profile.main_character.portrait_url(), main_name, avatar=True
            )
            main_corporation = main_character.corporation_name
            main_alliance = (
                main_character.alliance_name if main_character.alliance_name else ""
            )
            organization_html = format_html(
                "{}{}",
                main_corporation,
                f" [{main_character.alliance_ticker}]"
                if main_character.alliance_name
                else "",
            )
        else:
            main_html = main_name = ""
            main_corporation = main_alliance = organization_html = ""
        character_viewer_url = "{}?tab=skill_sets".format(
            reverse("memberaudit:character_viewer", args=[character.pk])
        )
        character_html = bootstrap_icon_plus_name_html(
            auth_character.portrait_url(),
            auth_character.character_name,
            avatar=True,
            url=character_viewer_url,
        )
        group_pk = group.pk if group else 0
        has_required = [
            bootstrap_icon_plus_name_html(
                obj.skill_set.ship_type.icon_url(
                    DEFAULT_ICON_SIZE, variant=EveType.IconVariant.REGULAR
                )
                if obj.skill_set.ship_type
                else eveimageserver.type_icon_url(
                    SKILL_SET_DEFAULT_ICON_TYPE_ID, size=DEFAULT_ICON_SIZE
                ),
                obj.skill_set.name,
            )
            for obj in skill_set_qs
        ]
        has_required_html = (
            "<br>".join(has_required)
            if has_required
            else '<i class="fas fa-times boolean-icon-false"></i>'
        )
        return {
            "id": f"{group_pk}_{character.pk}",
            "group": group.name_plus if group else UNGROUPED_SKILL_SET,
            "main": main_name,
            "main_html": main_html,
            "state": user.profile.state.name,
            "organization_html": organization_html,
            "corporation": main_corporation,
            "alliance": main_alliance,
            "character": character.character_ownership.character.character_name,
            "character_html": character_html,
            "has_required": has_required_html,
            "has_required_str": yesno_str(bool(has_required)),
            "is_doctrine_str": yesno_str(group.is_doctrine if group else False),
        }

    data = list()
    relevant_user_ids = list(
        General.accessible_users(request.user).exclude(
            profile__state__pk=get_guest_state_pk()
        )
    )
    character_qs = (
        Character.objects.select_related(
            "character_ownership__user",
            "character_ownership__user__profile__main_character",
            "character_ownership__character",
        )
        .prefetch_related("skill_set_checks")
        .filter(character_ownership__user__in=relevant_user_ids)
    )
    my_select_related = (
        "skill_set",
        "skill_set__ship_type",
        # "skill_set__ship_type__eve_group",
    )
    for group in SkillSetGroup.objects.all():
        for character in character_qs:
            skill_set_qs = (
                character.skill_set_checks.select_related(*my_select_related)
                .filter(skill_set__groups=group, failed_required_skills__isnull=True)
                .order_by("skill_set__name")
            )
            data.append(create_data_row(group, character))

    for character in character_qs:
        if (
            character.skill_set_checks.select_related("skill_set")
            .filter(skill_set__groups__isnull=True)
            .exists()
        ):
            skill_set_qs = (
                character.skill_set_checks.select_related(*my_select_related)
                .filter(
                    skill_set__groups__isnull=True, failed_required_skills__isnull=True
                )
                .order_by("skill_set__name")
            )
            data.append(create_data_row(None, character))

    return JsonResponse(data, safe=False)
