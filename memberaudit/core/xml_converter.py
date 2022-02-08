import re

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
    xml_doc = _remove_loc_tag(xml_doc)
    soup = BeautifulSoup(xml_doc, "html.parser")
    _convert_font_tag(soup)
    _convert_a_tag(soup)
    return str(soup)


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
        new_href = (
            element["href"] if is_string_an_url(href) else _match_eve_entity(href)
        )
        if new_href:
            element["href"] = new_href
            element["target"] = "_blank"
        else:
            element["href"] = "#"


def _match_eve_entity(href: str) -> str:
    link_match = re.match(
        r"(?P<schema>[a-zA-Z]+):(?P<type_id>\d+)\/\/(?P<entity_id>[0-9a-f]+)",
        href,
    )
    if link_match and link_match.group("schema") == "showinfo":
        type_id = int(link_match.group("type_id"))
        entity_id = link_match.group("entity_id")
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
