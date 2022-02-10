import ast
import re
import unicodedata

import bs4

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from eveuniverse.core import zkillboard
from eveuniverse.models import EveEntity, EveType

from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag

from .. import __title__
from ..constants import EveGroupId

logger = LoggerAddTag(get_extension_logger(__name__), __title__)

DEFAULT_FONT_SIZE = 13


def is_string_an_url(url_string: str) -> bool:
    """True if given string is an URL, else False"""
    validate_url = URLValidator()
    try:
        validate_url(url_string)
    except ValidationError:
        return False
    return True


def eve_xml_to_html(xml_doc: str, add_default_style: bool = False) -> str:
    """Converts Eve Online XML to HTML.

    Args:
    - xml_doc: XML document
    - add_default_style: When set true will add the default style to all unstyled fragments
    """
    xml_doc = _convert_unicode(xml_doc)

    # temporary fix to address u-bug in ESI endpoint for character bio
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
    soup = bs4.BeautifulSoup(xml_doc, "html.parser")
    _convert_font_tag(soup)
    _convert_a_tag(soup)
    if add_default_style:
        _add_default_style(soup)
    return str(soup)


def _convert_unicode(xml_doc: str) -> str:
    """Convert unicode encodings into UTF-8 characters."""
    try:
        xml_doc = xml_doc.encode("utf-8").decode("unicode-escape")
        xml_doc = unicodedata.normalize("NFKC", xml_doc)
    except ValueError:
        xml_doc = ""
    return xml_doc


def _remove_loc_tag(xml: str) -> str:
    """Remove all loc tags."""
    xml = xml.replace("<loc>", "")
    return xml.replace("</loc>", "")


def _convert_font_tag(soup):
    """Convert the font tags into HTML style."""
    for element in soup.find_all("font"):
        element.name = "span"
        styles = []
        if "size" in element.attrs:
            styles.append(f"font-size: {element['size']}px")
            del element["size"]
        if "color" in element.attrs:
            del element["color"]
        if styles:
            element["style"] = "; ".join(styles)


def _convert_a_tag(soup: bs4.BeautifulSoup):
    """Convert links into HTML."""
    for element in soup.find_all("a"):
        new_href = _eve_link_to_url(element["href"])
        if new_href:
            element["href"] = new_href
            element["target"] = "_blank"
        else:
            element["href"] = "#"


def _eve_link_to_url(href: str) -> str:
    """Convert an eve style link into a normal URL."""
    if is_string_an_url(href):
        return href
    showinfo_match = re.match(r"showinfo:(?P<type_id>\d+)\/\/(?P<entity_id>\d+)", href)
    if showinfo_match:
        return _convert_type_link(showinfo_match)
    killreport_match = re.match(
        r"killReport:(?P<killmail_id>\d+):(?P<killmail_hash>\w+)", href
    )
    if killreport_match:
        return _convert_killmail_link(killreport_match)
    return ""


def _convert_type_link(showinfo_match: re.Match) -> str:
    if showinfo_match:
        type_id = int(showinfo_match.group("type_id"))
        eve_type, _ = EveType.objects.get_or_create_esi(id=type_id)
        if eve_type.eve_group_id in {
            EveGroupId.ALLIANCE.value,
            EveGroupId.CHARACTER.value,
            EveGroupId.CORPORATION.value,
            EveGroupId.SOLAR_SYSTEM.value,
            EveGroupId.STATION.value,
        }:
            entity_id = showinfo_match.group("entity_id")
            eve_entity, _ = EveEntity.objects.get_or_create_esi(id=entity_id)
            return eve_entity.profile_url
    return ""


def _convert_killmail_link(killreport_match: re.Match) -> str:
    if killreport_match:
        killmail_id = int(killreport_match.group("killmail_id"))
        return zkillboard.killmail_url(killmail_id)
    return ""


def _add_default_style(soup: bs4.BeautifulSoup):
    """Add default style to all unstyled fragments."""
    for el in soup.children:
        if isinstance(el, bs4.NavigableString):
            new_tag = soup.new_tag("span")
            new_tag["style"] = f"font-size: {DEFAULT_FONT_SIZE}px"
            el.wrap(new_tag)
