from functools import wraps

from esi.models import Token
from esi.errors import TokenError

from django.http import HttpResponseForbidden, HttpResponseNotFound


def fetch_character_if_allowed(*args_select_related):
    """Asserts the current user has access to the character
    and loads the given character if it exists

    Args:
    - Optionally add list of parameters to be passed through to select_related().
    Note that "character_ownership" is already included.

    Returns:
    - 403 if user has no access
    - 404 if character does not exist
    """
    from .models import Character

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, character_pk, *args, **kwargs):
            try:
                args_select_related_2 = args_select_related + (
                    "character_ownership",
                    "character_ownership__character",
                )
                character = Character.objects.select_related(
                    *args_select_related_2
                ).get(pk=character_pk)
            except Character.DoesNotExist:
                return HttpResponseNotFound()

            if not character.user_has_access(request.user):
                return HttpResponseForbidden()

            return view_func(request, character_pk, character, *args, **kwargs)

        return _wrapped_view

    return decorator


def fetch_token(scopes=None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(character, *args, **kwargs):
            token = (
                Token.objects.prefetch_related("scopes")
                .filter(
                    user=character.character_ownership.user,
                    character_id=character.character_ownership.character.character_id,
                )
                .require_scopes(scopes if scopes else character.get_esi_scopes())
                .require_valid()
                .first()
            )
            if not token:
                raise TokenError("Could not find a matching token")

            return view_func(character, token, *args, **kwargs)

        return _wrapped_view

    return decorator