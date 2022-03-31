from dj_datatables_view.base_datatable_view import BaseDatatableView

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
def character_finder_data_old(request) -> JsonResponse:
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


class CharacterFinderListJson(BaseDatatableView):
    model = CharacterOwnership
    columns = [
        "character_id",
        "character",
        "character_organization",
        "main_character",
        "main_organization",
        "state_name",
        "actions",
        "alliance_name",
        "corporation_name",
        "main_alliance_name",
        "main_corporation_name",
        "main_str",
        "unregistered_str",
    ]

    # define column names that will be used in sorting
    # order is important and should be same as order of columns
    # displayed by datatables. For non sortable columns use empty
    # value like ''
    order_columns = [
        "character_id",
        "character",
        "character_organization",
        "main_character",
        "main_organization",
        "state_name",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    ]
    max_display_length = 500

    def get_initial_queryset(self):
        accessible_users = list(General.accessible_users(user=self.request.user))
        return CharacterOwnership.objects.filter(
            user__in=accessible_users
        ).select_related(
            "character",
            "memberaudit_character",
            "user",
            "user__profile__main_character",
            "user__profile__state",
        )

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter queryset

        # simple example:
        search = self.request.GET.get("search[value]", None)
        if search:
            qs = qs.filter(character__character_name__istartswith=search)
        return qs

    def render_column(self, row, column):
        # auth character related
        if column == "character_id":
            return row.character.character_id
        alliance_name = (
            row.character.alliance_name if row.character.alliance_name else ""
        )
        if column == "character_organization":
            return format_html(
                "{}<br><em>{}</em>",
                row.character.corporation_name,
                alliance_name,
            )
        if column == "alliance_name":
            return alliance_name
        if column == "corporation_name":
            return row.character.corporation_name
        # user related
        if column == "state_name":
            return row.user.profile.state.name
        # main related
        try:
            main_character = row.user.profile.main_character
        except AttributeError:
            main_character = None
            is_main = False
        else:
            is_main = row.user.profile.main_character == row.character
            main_alliance_name = (
                main_character.alliance_name if main_character.alliance_name else ""
            )
        if column == "main_character":
            if main_character:
                return bootstrap_icon_plus_name_html(
                    main_character.portrait_url(),
                    main_character.character_name,
                    avatar=True,
                )
            return ""
        if column == "main_organization":
            if main_character:
                return format_html(
                    "{}<br><em>{}</em>",
                    main_character.corporation_name,
                    main_alliance_name,
                )
            return ""
        if column == "main_alliance_name":
            return main_alliance_name if main_character else ""
        if column == "main_corporation_name":
            return main_character.corporation_name if main_character else ""
        if column == "main_str":
            if main_character:
                return yesno_str(is_main)
            return ""
        # member character related
        try:
            character = row.memberaudit_character
        except ObjectDoesNotExist:
            character = None
            character_viewer_url = ""
        else:
            character_viewer_url = reverse(
                "memberaudit:character_viewer", args=[character.pk]
            )
        if column == "character":
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
            return bootstrap_icon_plus_name_html(
                row.character.portrait_url(),
                row.character.character_name,
                avatar=True,
                url=character_viewer_url,
                text=character_text,
            )
        if column == "unregistered_str":
            return yesno_str(not bool(character))
        if column == "actions":
            if character:
                actions_html = fontawesome_link_button_html(
                    url=character_viewer_url,
                    fa_code="fas fa-search",
                    button_type="primary",
                )
            else:
                actions_html = ""
            return actions_html
        return super().render_column(row, column)
