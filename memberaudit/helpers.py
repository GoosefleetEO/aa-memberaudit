import re
import random
from time import sleep
from typing import Optional

import requests

from django.contrib.auth.models import User, Permission
from django.db import models
from django.db.models import Q
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from eveuniverse.models import EveSolarSystem, EveEntity
from allianceauth.eveonline.evelinks import dotlan, evewho
from allianceauth.services.hooks import get_extension_logger

from . import __title__, __version__
from .app_settings import MEMBERAUDIT_ESI_ERROR_LIMIT_THRESHOLD
from .utils import create_link_html, LoggerAddTag

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


def get_or_create_esi_or_none(
    prop_name: str, dct: dict, Model: type
) -> Optional[models.Model]:
    """tries to create a new eveuniverse object from a dictionary entry

    return the object on success or None
    """
    if dct.get(prop_name):
        obj, _ = Model.objects.get_or_create_esi(id=dct.get(prop_name))
    else:
        obj = None

    return obj


def get_or_create_or_none(
    prop_name: str, dct: dict, Model: type
) -> Optional[models.Model]:
    """tries to create a new Django object from a dictionary entry

    return the object on success or None
    """
    if dct.get(prop_name):
        obj, _ = Model.objects.get_or_create(id=dct.get(prop_name))
    else:
        obj = None

    return obj


def get_or_none(prop_name: str, dct: dict, Model: type) -> Optional[models.Model]:
    """tries to create a new Django object from a dictionary entry

    return the object on success or None
    """
    id = dct.get(prop_name)
    if id:
        try:
            return Model.objects.get(id=id)
        except Model.DoesNotExist:
            pass

    return None


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
        create_link_html(dotlan.solar_system_url(solar_system.name), solar_system.name),
        css_class,
        round(solar_system.security_status, 1),
        region_html,
    )


_font_regex = re.compile(
    r'<font (?P<pre>.*?)(size="(?P<size>[0-9]{1,2})")? ?(color="#[0-9a-f]{2}(?P<color>[0-9a-f]{6})")?(?P<post>.*?)>'
)
_link_regex = re.compile(
    r'<a href="(?P<schema>[a-zA-Z]+):(?P<first_id>\d+)((//|:)(?P<second_id>[0-9a-f]+))?">'
)


def _font_replace(font_match) -> str:
    pre = font_match.group("pre")  # before the color attr
    size = font_match.group("size")
    color = font_match.group("color")  # the raw color (eg. 'ffffff')
    post = font_match.group("post")  # after the color attr

    if color is None or color == "ffffff":
        color_attr = ""
    else:
        color_attr = f"color: #{color};"
    if size is None:
        size_attr = ""
    else:
        size_attr = f"font-size: {size}pt;"
    return f'<span {pre}style="{color_attr} {size_attr}"{post}>'


def _link_replace(link_match) -> str:
    schema = link_match.group("schema")
    first_id = int(link_match.group("first_id"))
    second_id = link_match.group("second_id")
    if schema == "showinfo":
        if second_id is not None:
            second_id = int(second_id)
        if 1373 <= first_id <= 1386:  # Character
            return f'<a href="{evewho.character_url(second_id)}" target="_blank">'
        elif first_id == 5:  # Solar System
            system_name = EveEntity.objects.resolve_name(second_id)
            return f'<a href="{dotlan.solar_system_url(system_name)}" target="_blank">'
        elif first_id == 2:  # Corporation
            corp_name = EveEntity.objects.resolve_name(second_id)
            return f'<a href="{dotlan.corporation_url(corp_name)}" target="_blank">'
        elif first_id == 16159:  # Alliance
            alliance_name = EveEntity.objects.resolve_name(second_id)
            return f'<a href="{dotlan.alliance_url(alliance_name)}" target="_blank">'
    return """<a href="javascript:showInvalidError();">"""


def eve_xml_to_html(xml: str) -> str:
    x = _font_regex.sub(_font_replace, xml)
    x = x.replace("</font>", "</span>")
    x = _link_regex.sub(_link_replace, x)
    # x = strip_tags(x)
    return mark_safe(x)


def users_with_permission(permission: Permission) -> models.QuerySet:
    """returns queryset of users that have the given permission in Auth"""
    users_qs = (
        User.objects.prefetch_related(
            "user_permissions", "groups", "profile__state__permissions"
        )
        .filter(
            Q(user_permissions=permission)
            | Q(groups__permissions=permission)
            | Q(profile__state__permissions=permission)
        )
        .distinct()
    )

    return users_qs


class EsiStatusException(Exception):
    """EsiStatus base exception"""

    def __init__(self, message):
        super().__init__()
        self.message = message


class EsiOffline(EsiStatusException):
    """ESI is offline"""

    def __init__(self):
        super().__init__("ESI appears to be offline")


class EsiErrorLimitExceeded(EsiStatusException):
    """ESI error limit exceeded"""

    def __init__(self, retry_in: float) -> None:
        retry_in = float(retry_in)
        super().__init__("The ESI error limit has been exceeded.")
        self.retry_in = retry_in  # seconds until next error window


class EsiStatus:
    """Current status of ESI (immutable)"""

    MAX_JITTER = 20

    def __init__(
        self,
        is_online: bool,
        error_limit_remain: int = None,
        error_limit_reset: int = None,
    ) -> None:
        self._is_online = bool(is_online)
        if error_limit_remain is None or error_limit_reset is None:
            self._error_limit_remain = None
            self._error_limit_reset = None
        else:
            self._error_limit_remain = int(error_limit_remain)
            self._error_limit_reset = int(error_limit_reset)

    @property
    def is_online(self) -> bool:
        return self._is_online

    @property
    def error_limit_remain(self) -> Optional[int]:
        return self._error_limit_remain

    @property
    def error_limit_reset(self) -> Optional[int]:
        return self._error_limit_reset

    @property
    def is_error_limit_exceeded(self) -> bool:
        """return True if remain is below the threshold, else False.

        Will also return False if remain/reset are not defined
        """
        return bool(
            self.error_limit_remain
            and self.error_limit_reset
            and self.error_limit_remain <= MEMBERAUDIT_ESI_ERROR_LIMIT_THRESHOLD
        )

    def error_limit_reset_w_jitter(self, max_jitter: int = None) -> int:
        """seconds to retry in order to reach next error window incl. jitter"""
        if self.error_limit_reset is None:
            return 0
        else:
            if not max_jitter or max_jitter < 1:
                max_jitter = self.MAX_JITTER

            return self.error_limit_reset + int(random.uniform(1, max_jitter))

    def raise_for_status(self):
        """will raise an exception derived from EsiStatusException
        if and only if conditions are met."""
        if not self.is_online:
            raise EsiOffline()

        if self.is_error_limit_exceeded:
            raise EsiErrorLimitExceeded(retry_in=self.error_limit_reset_w_jitter())


def fetch_esi_status() -> EsiStatus:
    """returns the current ESI online and error status"""
    max_retries = 3
    retries = 0
    while True:
        try:
            r = requests.get(
                "https://esi.evetech.net/latest/status/",
                timeout=(5, 30),
                headers={"User-Agent": f"{__title__};{__version__}"},
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            logger.warning("Network error when trying to call ESI", exc_info=True)
            return EsiStatus(
                is_online=False, error_limit_remain=None, error_limit_reset=None
            )
        if r.status_code not in {
            502,  # HTTPBadGateway
            503,  # HTTPServiceUnavailable
            504,  # HTTPGatewayTimeout
        }:
            break
        else:
            retries += 1
            if retries > max_retries:
                break
            else:
                logger.warning(
                    "HTTP status code %s - Retry %s/%s",
                    r.status_code,
                    retries,
                    max_retries,
                )
                wait_secs = 0.1 * (random.uniform(2, 4) ** (retries - 1))
                sleep(wait_secs)

    if not r.ok:
        is_online = False
    else:
        try:
            is_online = False if r.json().get("vip") else True
        except ValueError:
            is_online = False

    try:
        remain = int(r.headers.get("X-Esi-Error-Limit-Remain"))
        reset = int(r.headers.get("X-Esi-Error-Limit-Reset"))
    except TypeError:
        logger.warning("Failed to parse HTTP headers: %s", r.headers, exc_info=True)
        return EsiStatus(is_online=is_online)
    else:
        logger.debug(
            "ESI status: is_online: %s, error_limit_remain = %s, error_limit_reset = %s",
            is_online,
            remain,
            reset,
        )
        return EsiStatus(
            is_online=is_online, error_limit_remain=remain, error_limit_reset=reset
        )
