import ast
import re
import unicodedata
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from eveuniverse.models import EveEntity

from allianceauth.eveonline.evelinks import dotlan, evewho
from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag

from .. import __title__

logger = LoggerAddTag(get_extension_logger(__name__), __title__)

DEFAULT_TEXT_COLOR = "ffffffb3"  # RGBA in hex
ZKILLBOARD_KILL_URL = "https://zkillboard.com/kill/"


def is_string_an_url(url_string: str) -> bool:
    """True if given string is an URL, else False"""
    validate_url = URLValidator()
    try:
        validate_url(url_string)
    except ValidationError:
        return False
    return True


def eve_xml_to_html(xml_doc: str) -> str:
    """Converts Eve Online XML to HTML."""
    xml_doc = _convert_unicode(xml_doc)

    # temporary fix to address u-bug in ESI endpoint
    # workaround to address syntax error bug (#77)
    # see also: https://github.com/esi/esi-issues/issues/1265
    # TODO: remove when fixed
    if xml_doc.startswith("u'") and xml_doc.endswith("'"):
        try:
            xml_doc = ast.literal_eval(xml_doc)
        except SyntaxError:
            logger.warning("Failed to convert XML")
            xml_doc = ""
    xml_doc = _remove_loc_tag(xml_doc)
    soup = BeautifulSoup(xml_doc, "html.parser")
    _convert_font_tag(soup)
    _convert_a_tag(soup)
    return str(soup)


def _convert_unicode(xml_doc: str) -> str:
    try:
        xml_doc = xml_doc.encode("utf-8").decode("unicode-escape")
        xml_doc = unicodedata.normalize("NFKC", xml_doc)
    except ValueError:
        xml_doc = ""
    return xml_doc


def _remove_loc_tag(xml: str) -> str:
    xml = xml.replace("<loc>", "")
    return xml.replace("</loc>", "")


def _convert_font_tag(soup):
    for element in soup.find_all("font"):
        element.name = "span"
        styles = []
        if "size" in element.attrs:
            styles.append(f"font-size:{element['size']}")
            del element["size"]
        if "color" in element.attrs:
            color_ccp = element["color"].replace("#", "")
            try:
                hex_color = _ccp_color_to_rgba(color_ccp)
            except ValueError:
                hex_color = DEFAULT_TEXT_COLOR
            styles.append(f"color:#{hex_color}")
            del element["color"]
        if styles:
            element["style"] = ";".join(styles)


def _ccp_color_to_rgba(ccp_color) -> str:
    bytes = [ccp_color[i : i + 2] for i in range(0, len(ccp_color), 2)]
    try:
        return bytes[1] + bytes[2] + bytes[3] + bytes[0]
    except KeyError:
        raise ValueError from None


def _convert_a_tag(soup: BeautifulSoup):
    for element in soup.find_all("a"):
        href = element["href"]
        new_href = element["href"] if is_string_an_url(href) else _parse_eve_link(href)
        if new_href:
            element["href"] = new_href
            element["target"] = "_blank"
        else:
            element["href"] = "#"


def _parse_eve_link(href: str) -> str:
    showinfo_match = re.match(r"showinfo:(?P<type_id>\d+)\/\/(?P<entity_id>\d+)", href)
    if showinfo_match:
        type_id = int(showinfo_match.group("type_id"))
        entity_id = showinfo_match.group("entity_id")
        if entity_id is not None:
            entity_id = int(entity_id)
        if 1373 <= type_id <= 1386:  # Character
            return evewho.character_url(entity_id)
        elif type_id == 5:  # Solar System
            system_name = EveEntity.objects.resolve_name(entity_id)
            return dotlan.solar_system_url(system_name)
        elif type_id == 2:  # Corporation
            corp_name = EveEntity.objects.resolve_name(entity_id)
            return dotlan.corporation_url(corp_name)
        elif type_id == 16159:  # Alliance
            alliance_name = EveEntity.objects.resolve_name(entity_id)
            return dotlan.alliance_url(alliance_name)
        return None

    killreport_match = re.match(
        r"killReport:(?P<killmail_id>\d+):(?P<killmail_hash>\w+)", href
    )
    if killreport_match:
        killmail_id = int(killreport_match.group("killmail_id"))
        return urljoin(ZKILLBOARD_KILL_URL, str(killmail_id))
    return None
