"""Eve Online Fittings"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Iterable, List, Optional, Set, Tuple

from eveuniverse.models import EveEntity, EveType

from ..constants import EveCategoryId, EveGroupId
from .skills import Skill, compress_skills, required_skills_from_eve_types


class EftFormatError(ValueError):
    pass


@dataclass(frozen=True)
class _BaseFittingItem:
    def eve_types(self) -> Set[EveType]:
        raise NotImplementedError()

    def to_eft(self) -> str:
        raise NotImplementedError()

    def __init__(self) -> None:
        raise RuntimeError("No instantiation from abstract base class")


@dataclass(frozen=True)
class Module(_BaseFittingItem):
    """A ship module used in a fitting."""

    module_type: EveType
    charge_type: EveType = None
    is_offline: bool = False

    def eve_types(self) -> Set[EveType]:
        """Eve types used in this module."""
        types = {self.module_type}
        if self.charge_type:
            types.add(self.charge_type)
        return types

    def to_eft(self) -> str:
        """Convert to EFT format."""
        text = self.module_type.name
        if self.charge_type:
            text += f", {self.charge_type.name}"
        if self.is_offline:
            text += " /OFFLINE"
        return text


@dataclass(frozen=True)
class Item(_BaseFittingItem):
    """An item used in a fitting."""

    eve_type: EveType
    quantity: int

    def eve_types(self) -> Set[EveType]:
        """Eve types used in this item."""
        return {self.eve_type}

    def to_eft(self) -> str:
        """Convert to EFT format."""
        return f"{self.eve_type.name} x{self.quantity}"


@dataclass
class _EveTypes:
    """Container with EveType objects to enable quick name to object resolution."""

    objs: Dict[str, EveType] = field(default_factory=dict)

    def from_name(self, name: str) -> EveType:
        return self.objs[str(name)]

    @classmethod
    def create_from_names(cls, type_names: Iterable[str]) -> "_EveTypes":
        """Create new object from list of type names."""
        type_names = set(type_names)
        eve_types = cls._fetch_types_from_db(type_names)
        missing_type_names = type_names - set(eve_types.keys())
        if missing_type_names:
            eve_types = cls._fetch_missing_types_from_esi(
                type_names, missing_type_names, eve_types
            )
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
        type_names: Set[str],
        missing_type_names: Set[str],
        eve_types: Dict[str, EveType],
    ) -> Dict[str, EveType]:
        entity_ids = (
            EveEntity.objects.fetch_by_names_esi(missing_type_names)
            .filter(category=EveEntity.CATEGORY_INVENTORY_TYPE)
            .values_list("id", flat=True)
        )
        for entity_id in entity_ids:
            obj, _ = EveType.objects.get_or_create_esi(
                id=entity_id, enabled_sections=[EveType.Section.DOGMAS]
            )
            eve_types[obj.name] = obj
        missing_type_names = type_names - set(eve_types.keys())
        if missing_type_names:
            raise EftFormatError(
                f"Types with these names do not exist: {missing_type_names}"
            )
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
            return eve_type.eve_group.eve_category_id
        return None

    def group_id(self, eve_types: _EveTypes) -> Optional[int]:
        """Category ID of this item or None"""
        if self.item_type:
            eve_type = eve_types.from_name(self.item_type)
            return eve_type.eve_group_id
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
        part = line.split()[-1]
        if "x" in part and part[1:].isdigit():
            item_type = line.split(part)[0].strip()
            quantity = part[1:]
            return cls(item_type=item_type, quantity=quantity)
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
        BOOSTER = auto()
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
                return self.Category.BOOSTER
            elif group_id == EveGroupId.CYBERIMPLANT:
                return self.Category.IMPLANTS
        return None

    def to_modules(self, eve_types: _EveTypes) -> List[Module]:
        objs = []
        for item in self.items:
            if item.is_empty:
                objs.append(None)
            else:
                params = {
                    "module_type": eve_types.from_name(item.item_type),
                    "is_offline": item.is_offline,
                }
                if item.charge_type:
                    params["charge_type"] = eve_types.from_name(item.charge_type)
                objs.append(Module(**params))
        return objs

    def to_items(self, eve_types: _EveTypes) -> List[Module]:
        objs = []
        for item in self.items:
            params = {"eve_type": eve_types.from_name(item.item_type)}
            if item.quantity:
                params["quantity"] = item.quantity
            objs.append(Item(**params))
        return objs

    @classmethod
    def create_from_lines(cls, lines, category):
        if category.is_slots:
            items = [_EftItem.create_from_slots(line) for line in lines]
        else:
            items = [_EftItem.create_from_non_slots(line) for line in lines]
        return cls(items=items, category=category)


@dataclass(frozen=True)
class Fitting:
    """A fitting for a ship in Eve Online."""

    name: str
    ship_type: EveType
    high_slots: List[Optional[Module]] = field(default_factory=list)
    medium_slots: List[Optional[Module]] = field(default_factory=list)
    low_slots: List[Optional[Module]] = field(default_factory=list)
    rig_slots: List[Optional[Module]] = field(default_factory=list)
    drone_bay: List[Item] = field(default_factory=list)
    fighter_bay: List[Item] = field(default_factory=list)
    cargo_bay: List[Item] = field(default_factory=list)
    fitting_notes: str = ""

    def __str__(self) -> str:
        return f"{self.name}"

    @property
    def modules(self) -> List[EveType]:
        """All fitted modules."""
        return self.high_slots + self.medium_slots + self.low_slots + self.rig_slots

    def eve_types(self, include_cargo=True) -> Set[EveType]:
        """Types of all modules and items."""
        objs = self.modules + self.drone_bay + self.fighter_bay
        if include_cargo:
            objs += self.cargo_bay
        types = {self.ship_type}
        for obj in [x for x in objs if x]:
            types |= {eve_type for eve_type in obj.eve_types()}
        return types

    def required_skills(self) -> List[Skill]:
        """Skills required to fly this fitting."""

        eve_types = self.eve_types(include_cargo=False)
        skills = required_skills_from_eve_types(eve_types)
        return compress_skills(skills)

    def to_eft(self) -> str:
        def add_section(objs, keyword: str = None) -> List[str]:
            lines = [""]
            for obj in objs:
                lines.append(obj.to_eft() if obj else f"[Empty {keyword} slot]")
            return lines

        lines = []
        lines.append(f"[{self.ship_type.name}, {self.name}]")
        lines += add_section(self.low_slots, "Low")
        lines += add_section(self.medium_slots, "Med")
        lines += add_section(self.high_slots, "High")
        lines += add_section(self.rig_slots, "Rig")
        if self.drone_bay:
            lines.append("")
            lines += add_section(self.drone_bay)
        if self.fighter_bay:
            lines.append("")
            lines += add_section(self.fighter_bay)
        if self.cargo_bay:
            lines.append("")
            lines += add_section(self.cargo_bay)
        return "\n".join(lines)

    @classmethod
    def create_from_eft(cls, eft_text: str) -> "Fitting":
        """Create new object from fitting in EFT format."""
        lines = cls._text_into_lines(eft_text)
        text_sections = cls._lines_to_text_sections(lines)
        sections = cls._text_sections_to_eft_sections(text_sections)
        ship_type_name, fitting_name = cls._parse_title(lines[0])
        eve_types = cls._load_eve_types(ship_type_name, sections)
        sections = cls._try_to_identify_unknown_sections(sections, eve_types)
        fitting = cls._create_fitting_from_sections(
            sections, ship_type_name, fitting_name, eve_types
        )
        return fitting

    @classmethod
    def _text_into_lines(cls, eft_text: str) -> List[str]:
        """Convert text into lines."""
        lines = eft_text.strip().splitlines()
        if not lines:
            raise EftFormatError("Text is empty")
        return lines

    @staticmethod
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

    @staticmethod
    def _text_sections_to_eft_sections(
        text_sections: List[List[str]],
    ) -> List[_EftSection]:
        """Create eft sections from text sections."""
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

    @staticmethod
    def _parse_title(line: str) -> Tuple[str, str]:
        """Try to parse title from lines."""
        if line.startswith("[") and "," in line:
            ship_type_name, fitting_name = line[1:-1].split(",")
            return ship_type_name.strip(), fitting_name.strip()
        raise EftFormatError("Title not found")

    @staticmethod
    def _load_eve_types(ship_type_name: str, sections: List[_EftSection]) -> _EveTypes:
        """Load all EveType objects used in this fitting."""
        type_names = {ship_type_name}
        for section in sections:
            type_names |= section.type_names()
        return _EveTypes.create_from_names(type_names)

    @staticmethod
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

    @staticmethod
    def _create_fitting_from_sections(
        sections: List[_EftSection],
        ship_type_name: str,
        fitting_name: str,
        eve_types: _EveTypes,
    ) -> "Fitting":
        """Create fitting object from input."""
        params = {
            "name": fitting_name,
            "ship_type": eve_types.from_name(ship_type_name),
        }
        for section in sections:
            if section.category == _EftSection.Category.HIGH_SLOTS:
                params["high_slots"] = section.to_modules(eve_types)
            elif section.category == _EftSection.Category.MEDIUM_SLOTS:
                params["medium_slots"] = section.to_modules(eve_types)
            elif section.category == _EftSection.Category.LOW_SLOTS:
                params["low_slots"] = section.to_modules(eve_types)
            elif section.category == _EftSection.Category.RIG_SLOTS:
                params["rig_slots"] = section.to_modules(eve_types)
            elif section.category == _EftSection.Category.DRONES_BAY:
                params["drone_bay"] = section.to_items(eve_types)
            elif section.category == _EftSection.Category.FIGHTER_BAY:
                params["fighter_bay"] = section.to_items(eve_types)
            elif section.category == _EftSection.Category.CARGO_BAY:
                params["cargo_bay"] = section.to_items(eve_types)
        return Fitting(**params)
