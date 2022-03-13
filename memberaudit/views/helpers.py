from django.utils.translation import gettext_lazy

from ..app_settings import MEMBERAUDIT_APP_NAME
from ..constants import MY_DATETIME_FORMAT
from ..models import Character

UNGROUPED_SKILL_SET = gettext_lazy("[Ungrouped]")


def add_common_context(request, context: dict) -> dict:
    """adds the common context used by all view"""
    unregistered_count = Character.objects.unregistered_characters_of_user_count(
        request.user
    )
    new_context = {
        **{
            "app_title": MEMBERAUDIT_APP_NAME,
            "unregistered_count": unregistered_count,
            "MY_DATETIME_FORMAT": MY_DATETIME_FORMAT,
        },
        **context,
    }
    return new_context
