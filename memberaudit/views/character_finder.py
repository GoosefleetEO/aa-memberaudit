from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag
from app_utils.views import (
    bootstrap_icon_plus_name_html,
    fontawesome_link_button_html,
    yesno_str,
)

from .. import __title__
from ..models import General
from ._common import add_common_context

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
    accessible_users = list(General.accessible_users(user=request.user))
    for character_ownership in CharacterOwnership.objects.filter(
        user__in=accessible_users
    ).select_related(
        "character",
        "memberaudit_character",
        "user",
        "user__profile__main_character",
        "user__profile__state",
    ):
        auth_character = character_ownership.character
        try:
            character = character_ownership.memberaudit_character
        except ObjectDoesNotExist:
            character = None
            character_viewer_url = ""
            actions_html = ""
        else:
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
        user_profile = character_ownership.user.profile
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

        is_main = character_ownership.user.profile.main_character == auth_character
        icons = []
        if is_main:
            icons.append(
                mark_safe('<i class="fas fa-crown" title="Main character"></i>')
            )
        if character and character.is_shared:
            icons.append(
                mark_safe('<i class="far fa-eye" title="Shared character"></i>')
            )
        if not character:
            icons.append(
                mark_safe(
                    '<i class="fas fa-exclamation-triangle" title="Unregistered character"></i>'
                )
            )
        character_text = format_html_join(
            mark_safe("&nbsp;"), "{}", ([html] for html in icons)
        )
        character_html = bootstrap_icon_plus_name_html(
            auth_character.portrait_url(),
            auth_character.character_name,
            avatar=True,
            url=character_viewer_url,
            text=character_text,
        )
        alliance_name = (
            auth_character.alliance_name if auth_character.alliance_name else ""
        )
        character_list.append(
            {
                "character_id": auth_character.character_id,
                "character": {
                    "display": character_html,
                    "sort": auth_character.character_name,
                },
                "character_organization": character_organization,
                "main_character": main_html,
                "main_organization": main_organization,
                "state_name": user_profile.state.name,
                "actions": actions_html,
                "alliance_name": alliance_name,
                "corporation_name": auth_character.corporation_name,
                "main_alliance_name": main_alliance,
                "main_corporation_name": main_corporation,
                "main_str": yesno_str(is_main),
                "unregistered_str": yesno_str(not bool(character)),
            }
        )
    return JsonResponse({"data": character_list})
