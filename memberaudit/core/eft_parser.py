"""Parser for fitting in EFT Format"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Iterable, List, Optional, Set, Tuple

from bravado.exception import HTTPNotFound

from eveuniverse.models import EveEntity, EveType

from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag

from .. import __title__
from ..constants import EveCategoryId, EveGroupId
from .fittings import Fitting, Item, Module

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


class EftParserError(Exception):
    """Base error for EFT parser."""


class MissingTitleError(EftParserError):
    """Title is missing."""


class MissingSectionsError(EftParserError):
    """Insufficient sections defined."""


@dataclass
class _EveTypes:
    """Container with EveType objects to enable quick name to object resolution."""

    objs_by_name: Dict[str, EveType] = field(default_factory=dict)

    def from_name(self, type_name: str) -> Optional[EveType]:
        """Resolve given type name into EveType object.

        Returns ``None`` if it can not be resolved.
        """
        return self.objs_by_name.get(str(type_name))

    @classmethod
    def create_from_names(
        cls, type_names: Iterable[str]
    ) -> Tuple["_EveTypes", Set[str]]:
        """Create new object from list of type names.

        Will try to fetch types from DB first and load missing types from ESI.
        All types must have dogmas.

        Returns:
            created object, list of type names that could not be resolved
        """
        type_names = set(type_names)
        eve_types = cls._fetch_types_from_db(type_names)
        missing_type_names = type_names - set(eve_types.keys())
        if missing_type_names:
            eve_types.update(cls._fetch_missing_types_from_esi(missing_type_names))
        return cls(eve_types)

    @classmethod
    def _fetch_types_from_db(cls, type_names: Iterable[str]) -> Dict[str, EveType]:
        eve_types_query = EveType.objects.select_related("eve_group").filter(
            enabled_sections=EveType.enabled_sections.dogmas, name__in=type_names
        )
        eve_types = {obj.name: obj for obj in eve_types_query}
        return eve_types

    @staticmethod
    def _fetch_missing_types_from_esi(
        missing_type_names: Set[str],
    ) -> Dict[str, EveType]:
        entity_ids = (
            EveEntity.objects.fetch_by_names_esi(missing_type_names)
            .filter(category=EveEntity.CATEGORY_INVENTORY_TYPE)
            .values_list("id", flat=True)
        )
        eve_types = dict()
        for entity_id in entity_ids:
            try:
                obj, _ = EveType.objects.get_or_create_esi(
                    id=entity_id, enabled_sections=[EveType.Section.DOGMAS]
                )
                eve_types[obj.name] = obj
            except HTTPNotFound:
                pass
        return eve_types


@dataclass
class _EftItem:
    """Item of an EFT fitting used for parsing."""

    item_type: str = None
    charge_type: str = None
    quantity: int = None
    is_offline: bool = False
    is_empty: bool = False

    def type_names(self) -> Set[str]:
        types = set()
        if self.item_type:
            types.add(self.item_type)
        if self.charge_type:
            types.add(self.charge_type)
        return types

    def category_id(self, eve_types: _EveTypes) -> Optional[int]:
        """Category ID of this item or None"""
        if self.item_type:
            eve_type = eve_types.from_name(self.item_type)
            return eve_type.eve_group.eve_category_id if eve_type else None
        return None

    def group_id(self, eve_types: _EveTypes) -> Optional[int]:
        """Category ID of this item or None"""
        if self.item_type:
            eve_type = eve_types.from_name(self.item_type)
            return eve_type.eve_group_id if eve_type else None
        return None

    @classmethod
    def create_from_slots(cls, line: str) -> "_EftItem":
        if "empty" in line.strip("[]").lower():
            return cls(is_empty=True)
        if "/OFFLINE" in line:
            is_offline = True
            line = line.replace(" /OFFLINE", "")
        else:
            is_offline = False
        if "," in line:
            item_type, charge_type = line.split(",")
            charge_type = charge_type.strip()
            return cls(
                item_type=item_type, charge_type=charge_type, is_offline=is_offline
            )
        return cls(item_type=line.strip(), is_offline=is_offline)

    @classmethod
    def create_from_non_slots(cls, line: str) -> "_EftItem":
        if "empty" in line.strip("[]").lower():  # for structure services
            return cls(is_empty=True)
        part = line.split()[-1]
        if "x" in part and part[1:].isdigit():
            item_type = line.split(part)[0].strip()
            quantity = part[1:]
            return cls(item_type=item_type, quantity=int(quantity))
        return cls(item_type=line.strip())


@dataclass
class _EftSection:
    """Section of an EFT fitting used for parsing."""

    class Category(Enum):
        UNKNOWN = auto()
        HIGH_SLOTS = auto()
        MEDIUM_SLOTS = auto()
        LOW_SLOTS = auto()
        RIG_SLOTS = auto()
        DRONES_BAY = auto()
        FIGHTER_BAY = auto()
        IMPLANTS = auto()
        BOOSTERS = auto()
        CARGO_BAY = auto()

        @property
        def is_slots(self) -> bool:
            return self in {
                self.HIGH_SLOTS,
                self.MEDIUM_SLOTS,
                self.LOW_SLOTS,
                self.RIG_SLOTS,
            }

    items: List[_EftItem] = field(default_factory=list)
    category: Category = Category.UNKNOWN

    def type_names(self) -> Set[str]:
        types = set()
        for item in self.items:
            types |= item.type_names()
        return types

    def category_ids(self, eve_types: _EveTypes) -> Set[Optional[int]]:
        return {item.category_id(eve_types) for item in self.items}

    def group_ids(self, eve_types: _EveTypes) -> Set[Optional[int]]:
        return {item.group_id(eve_types) for item in self.items}

    def guess_category(self, eve_types: _EveTypes) -> Optional["_EftSection.Category"]:
        """Try to guess the category of this section based on it's items.
        Returns ``None`` if the guess fails.
        """
        ids = self.category_ids(eve_types)
        if len(ids) != 1:
            return None
        category_id = ids.pop()
        if category_id == EveCategoryId.DRONE:
            return self.Category.DRONES_BAY
        elif category_id == EveCategoryId.FIGHTER:
            return self.Category.FIGHTER_BAY
        elif category_id == EveCategoryId.IMPLANT:
            ids = self.group_ids(eve_types)
            if len(ids) != 1:
                return None
            group_id = ids.pop()
            if group_id == EveGroupId.BOOSTER:
                return self.Category.BOOSTERS
            elif group_id == EveGroupId.CYBERIMPLANT:
                return self.Category.IMPLANTS
        return None

    def to_modules(self, eve_types: _EveTypes) -> Tuple[List[Module], Set[str]]:
        """Convert eft items into fitting modules.

        Types from modules that can not be resolved will result in an empty slot.
        """
        objs = []
        unknown_types = set()
        for item in self.items:
            if item.is_empty:
                objs.append(None)
            else:
                params = {"is_offline": item.is_offline}
                module_type = eve_types.from_name(item.item_type)
                if module_type:
                    params["module_type"] = module_type
                    if item.charge_type:
                        charge_type = eve_types.from_name(item.charge_type)
                        if charge_type:
                            params["charge_type"] = charge_type
                        else:
                            unknown_types.add(item.charge_type)
                    objs.append(Module(**params))
                else:
                    objs.append(None)
                    unknown_types.add(item.item_type)
        return objs, unknown_types

    def to_items(self, eve_types: _EveTypes) -> Tuple[List[Module], Set[str]]:
        """Convert eft items into fitting items."""
        objs = []
        unknown_types = set()
        for item in self.items:
            if item.is_empty:
                continue
            params = dict()
            item_type = eve_types.from_name(item.item_type)
            if item_type:
                params["item_type"] = item_type
                if item.quantity:
                    params["quantity"] = item.quantity
                objs.append(Item(**params))
            else:
                unknown_types.add(item.item_type)
        return objs, unknown_types

    @classmethod
    def create_from_lines(cls, lines, category):
        if category.is_slots:
            items = [_EftItem.create_from_slots(line) for line in lines]
        else:
            items = [_EftItem.create_from_non_slots(line) for line in lines]
        return cls(items=items, category=category)


def create_fitting_from_eft(eft_text: str) -> Tuple[Fitting, List[str]]:
    """Create new object from fitting in EFT format."""
    lines = _text_into_lines(eft_text)
    text_sections = _lines_to_text_sections(lines)
    sections = _text_sections_to_eft_sections(text_sections)
    ship_type_name, fitting_name = _parse_title(lines[0])
    eve_types = _load_eve_types(ship_type_name, sections)
    sections = _try_to_identify_unknown_sections(sections, eve_types)
    fitting, unknown_types = _create_fitting_from_sections(
        sections, ship_type_name, fitting_name, eve_types
    )
    errors = _unknown_types_to_errors(unknown_types)
    return fitting, errors


def _text_into_lines(eft_text: str) -> List[str]:
    """Convert text into lines."""
    lines = eft_text.strip().splitlines()
    if not lines:
        raise MissingSectionsError("Text is empty")
    return lines


def _lines_to_text_sections(lines: List[str]) -> List[List[str]]:
    """Split lines into text sections."""
    text_sections = []
    section_lines = []
    for line in lines[1:]:
        if line:
            section_lines.append(line)
        else:
            if section_lines:
                text_sections.append(section_lines)
                section_lines = []
    if section_lines:
        text_sections.append(section_lines)
    return text_sections


def _text_sections_to_eft_sections(
    text_sections: List[List[str]],
) -> List[_EftSection]:
    """Create eft sections from text sections."""
    if len(text_sections) < 4:
        raise MissingSectionsError("Must contain at least 4 sections.")
    slot_categories = [
        _EftSection.Category.LOW_SLOTS,
        _EftSection.Category.MEDIUM_SLOTS,
        _EftSection.Category.HIGH_SLOTS,
        _EftSection.Category.RIG_SLOTS,
    ]
    sections = []
    for num, section_lines in enumerate(text_sections):
        if num < 4:
            category = slot_categories[num]
        else:
            category = _EftSection.Category.UNKNOWN
        sections.append(
            _EftSection.create_from_lines(lines=section_lines, category=category)
        )
    return sections


def _parse_title(line: str) -> Tuple[str, str]:
    """Try to parse title from lines."""
    if line.startswith("[") and "," in line:
        ship_type_name, fitting_name = line[1:-1].split(",")
        return ship_type_name.strip(), fitting_name.strip()
    raise MissingTitleError("Title not found")


def _load_eve_types(ship_type_name: str, sections: List[_EftSection]) -> _EveTypes:
    """Load all EveType objects used in this fitting."""
    type_names = {ship_type_name}
    for section in sections:
        type_names |= section.type_names()
    eve_types = _EveTypes.create_from_names(type_names)
    return eve_types


def _try_to_identify_unknown_sections(
    sections: List[_EftSection], eve_types: _EveTypes
) -> List[_EftSection]:
    """Identify unknown section if possible."""
    for section in sections:
        if section.category == _EftSection.Category.UNKNOWN:
            category = section.guess_category(eve_types)
            if category:
                section.category = category
    # last unknown section (if any remain) must be the cargo bay
    unknown_sections = [
        section
        for section in sections
        if section.category == _EftSection.Category.UNKNOWN
    ]
    if unknown_sections:
        unknown_sections.pop().category = _EftSection.Category.CARGO_BAY
    return sections


def _create_fitting_from_sections(
    sections: List[_EftSection],
    ship_type_name: str,
    fitting_name: str,
    eve_types: _EveTypes,
) -> Tuple[Fitting, Set[str]]:
    """Create fitting object from input."""
    params = {
        "name": fitting_name,
        "ship_type": eve_types.from_name(ship_type_name),
    }
    all_unknown_types = set()
    for section in sections:
        if section.category == _EftSection.Category.HIGH_SLOTS:
            params["high_slots"], unknown_types = section.to_modules(eve_types)
        elif section.category == _EftSection.Category.MEDIUM_SLOTS:
            params["medium_slots"], unknown_types = section.to_modules(eve_types)
        elif section.category == _EftSection.Category.LOW_SLOTS:
            params["low_slots"], unknown_types = section.to_modules(eve_types)
        elif section.category == _EftSection.Category.RIG_SLOTS:
            params["rig_slots"], unknown_types = section.to_modules(eve_types)
        elif section.category == _EftSection.Category.DRONES_BAY:
            params["drone_bay"], unknown_types = section.to_items(eve_types)
        elif section.category == _EftSection.Category.FIGHTER_BAY:
            params["fighter_bay"], unknown_types = section.to_items(eve_types)
        elif section.category == _EftSection.Category.IMPLANTS:
            params["implants"], unknown_types = section.to_items(eve_types)
        elif section.category == _EftSection.Category.BOOSTERS:
            params["boosters"], unknown_types = section.to_items(eve_types)
        elif section.category == _EftSection.Category.CARGO_BAY:
            params["cargo_bay"], unknown_types = section.to_items(eve_types)
        all_unknown_types |= unknown_types
    return Fitting(**params), all_unknown_types


def _unknown_types_to_errors(unknown_types: Set[str]) -> List[str]:
    errors = []
    if unknown_types:
        names = ", ".join(sorted(list(unknown_types)))
        errors.append(f"Ignored modules/items with unknown types: {names}")
    return errors
