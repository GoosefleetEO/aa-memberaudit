from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag
from app_utils.views import (
    bootstrap_icon_plus_name_html,
    fontawesome_link_button_html,
    yesno_str,
)

from .. import __title__
from ..models import Character
from ._common import add_common_context, eve_solar_system_to_html

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


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
