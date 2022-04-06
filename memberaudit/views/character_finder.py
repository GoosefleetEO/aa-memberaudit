from dj_datatables_view.base_datatable_view import BaseDatatableView

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Case, Q, Value, When
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


class CharacterFinderListJson(
    PermissionRequiredMixin, LoginRequiredMixin, BaseDatatableView
):
    model = CharacterOwnership
    permission_required = "memberaudit.finder_access"
    columns = [
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
        "character_id",
    ]

    # define column names that will be used in sorting
    # order is important and should be same as order of columns
    # displayed by datatables. For non sortable columns use empty
    # value like ''
    order_columns = [
        "character__character_name",
        "character__corporation_name",
        "user__profile__main_character__character_name",
        "user__profile__main_character__corporation_name",
        "user__profile__state__state_name",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    ]

    def get_initial_queryset(self):
        return self.initial_queryset(self.request)

    @classmethod
    def initial_queryset(cls, request):
        accessible_users = list(General.accessible_users(user=request.user))
        my_filter = Q(user__in=accessible_users)
        if request.user.has_perm("memberaudit.view_shared_characters"):
            my_filter |= Q(memberaudit_character__is_shared=True)
        character_ownerships = CharacterOwnership.objects.select_related(
            "character",
            "memberaudit_character",
            "user",
            "user__profile__main_character",
            "user__profile__state",
        ).filter(my_filter)
        return character_ownerships.annotate(
            unregistered=Case(
                When(memberaudit_character=None, then=Value("yes")),
                default=Value("no"),
            )
        )

    def filter_queryset(self, qs):
        """use parameters passed in GET request to filter queryset"""

        qs = self._apply_search_filter(qs, 4, "user__profile__state__name")
        qs = self._apply_search_filter(qs, 6, "character__alliance_name")
        qs = self._apply_search_filter(qs, 7, "character__corporation_name")
        qs = self._apply_search_filter(
            qs, 8, "user__profile__main_character__alliance_name"
        )
        qs = self._apply_search_filter(
            qs, 9, "user__profile__main_character__corporation_name"
        )
        qs = self._apply_search_filter(
            qs, 10, "user__profile__main_character__character_name"
        )
        qs = self._apply_search_filter(qs, 11, "unregistered")

        search = self.request.GET.get("search[value]", None)
        if search:
            qs = qs.filter(
                Q(character__character_name__istartswith=search)
                | Q(user__profile__main_character__character_name__istartswith=search)
            )
        return qs

    def _apply_search_filter(self, qs, column_num, field):
        my_filter = self.request.GET.get(f"columns[{column_num}][search][value]", None)
        if my_filter:
            if self.request.GET.get(f"columns[{column_num}][search][regex]", False):
                kwargs = {f"{field}__iregex": my_filter}
            else:
                kwargs = {f"{field}__istartswith": my_filter}
            return qs.filter(**kwargs)
        return qs

    def render_column(self, row, column):
        result = self._render_column_general(row, column)
        if result:
            return result
        result = self._render_column_auth_character(row, column)
        if result:
            return result
        result = self._render_column_main_character(row, column)
        if result:
            return result
        result = self._render_column_memberaudit_character(row, column)
        if result:
            return result
        return super().render_column(row, column)

    def _render_column_general(self, row, column):
        if column == "state_name":
            return row.user.profile.state.name
        if column == "unregistered_str":
            return row.unregistered
        return None

    def _render_column_auth_character(self, row, column):
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
        return None

    def _render_column_main_character(self, row, column):
        try:
            main_character = row.user.profile.main_character
        except AttributeError:
            main_character = None
            is_main = False
        else:
            is_main = row.user.profile.main_character == row.character
            main_alliance_name = (
                main_character.alliance_name
                if main_character and main_character.alliance_name
                else ""
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
        return None

    def _render_column_memberaudit_character(self, row, column):
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
            try:
                is_main = row.user.profile.main_character == row.character
            except AttributeError:
                is_main = False
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
        if column == "actions":
            if character_viewer_url:
                actions_html = fontawesome_link_button_html(
                    url=character_viewer_url,
                    fa_code="fas fa-search",
                    button_type="primary",
                )
            else:
                actions_html = ""
            return actions_html
        return None


@login_required
@permission_required("memberaudit.finder_access")
def character_finder_list_fdd_data(request) -> JsonResponse:
    """Provide lists for drop down fields."""
    result = dict()
    qs = CharacterFinderListJson.initial_queryset(request)
    columns = request.GET.get("columns")
    if columns:
        for column in columns.split(","):
            if column == "alliance_name":
                options = qs.exclude(character__alliance_id__isnull=True).values_list(
                    "character__alliance_name", flat=True
                )
            elif column == "corporation_name":
                options = qs.values_list("character__corporation_name", flat=True)
            elif column == "main_alliance_name":
                options = qs.exclude(
                    Q(user__profile__main_character__isnull=True)
                    | Q(user__profile__main_character__alliance_id__isnull=True)
                ).values_list("user__profile__main_character__alliance_name", flat=True)
            elif column == "main_corporation_name":
                options = qs.exclude(
                    user__profile__main_character__isnull=True
                ).values_list(
                    "user__profile__main_character__corporation_name", flat=True
                )
            elif column == "main_str":
                options = qs.exclude(
                    user__profile__main_character__isnull=True
                ).values_list(
                    "user__profile__main_character__character_name", flat=True
                )
            elif column == "unregistered_str":
                options = map(
                    lambda x: "yes" if x is None else "no",
                    qs.values_list("memberaudit_character", flat=True),
                )
            elif column == "state_name":
                options = qs.values_list("user__profile__state__name", flat=True)
            else:
                options = [f"** ERROR: Invalid column name '{column}' **"]
            result[column] = sorted(list(set(options)), key=str.casefold)
    return JsonResponse(result, safe=False)
