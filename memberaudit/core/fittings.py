"""Eve Online Fittings"""
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Set

from eveuniverse.models import EveEntity, EveType

from ..constants import EveCategoryId
from .skills import Skill


@dataclass(frozen=True)
class Module:
    """A ship module used in a fitting."""

    module_type: EveType
    charge_type: EveType = None

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
        return text


@dataclass(frozen=True)
class Item:
    """An item used in a fitting."""

    eve_type: EveType
    quantity: int

    def eve_types(self) -> Set[EveType]:
        """Eve types used in this item."""
        return {self.eve_type}

    def to_eft(self) -> str:
        """Convert to EFT format."""
        return f"{self.eve_type.name} x{self.quantity}"


@dataclass(frozen=True)
class Fitting:
    """A fitting for a ship in Eve Online."""

    name: str
    ship_type: EveType
    high_slots: List[Optional[Module]] = field(default_factory=list)
    medium_slots: List[Optional[Module]] = field(default_factory=list)
    low_slots: List[Optional[Module]] = field(default_factory=list)
    rigs: List[Optional[Module]] = field(default_factory=list)
    cargo_bay: List[Item] = field(default_factory=list)
    drone_bay: List[Item] = field(default_factory=list)
    fighter_bay: List[Item] = field(default_factory=list)
    fitting_notes: str = ""

    def __str__(self) -> str:
        return f"{self.name}"

    @property
    def modules(self) -> List[EveType]:
        """All fitted modules."""
        return self.high_slots + self.medium_slots + self.low_slots + self.rigs

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

        skills = self._required_skills_raw()
        return Skill.compress_skills(skills)

    def _required_skills_raw(self):
        skills = []
        for eve_type in self.eve_types(include_cargo=False):
            required_skills = Skill.create_from_eve_type(eve_type)
            if required_skills:
                skills += required_skills
        return skills

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
        lines += add_section(self.rigs, "Rig")
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
        """Create new fitting from fitting in EFT format."""
        eft_lines = eft_text.strip().splitlines()
        parsed_fitting_notes = cls._removeOfflinedModulesMention(eft_lines)
        sections = [
            section
            for section in _Section.create_from_lines(parsed_fitting_notes["eft_lines"])
        ]
        slots = []
        cargo_bay = []
        drone_bay = []
        fighter_bay = []
        ship_type = ""
        fit_name = ""
        for section in sections:
            if section.is_drone_bay():
                drone_bay = section.parse_bay()
            elif section.is_fighter_bay():
                fighter_bay = section.parse_bay()
            else:
                modules = []
                for line in section.lines:
                    if line.startswith("["):
                        if "," in line:
                            # fitting title
                            ship_type_name, fit_name = line[1:-1].split(",")
                            ship_type = _fetch_eve_type(ship_type_name)
                        elif "empty" in line.strip("[]").lower():
                            # empty slot
                            modules.append(None)
                    else:
                        if "," in line:
                            module_name, charge_name = line.split(",")
                            module_type = _fetch_eve_type(module_name)
                            charge_type = _fetch_eve_type(charge_name.strip())
                            modules.append(
                                Module(module_type=module_type, charge_type=charge_type)
                            )
                        else:
                            quantity = line.split()[
                                -1
                            ]  # Quantity will always be the last element, if it is there.
                            if "x" in quantity and quantity[1:].isdigit():
                                item_name = line.split(quantity)[0].strip()
                                eve_type = _fetch_eve_type(item_name)
                                cargo_bay.append(
                                    Item(
                                        eve_type=eve_type,
                                        quantity=int(quantity.strip("x")),
                                    )
                                )
                            else:
                                module_name = line.strip()
                                eve_type = _fetch_eve_type(module_name)
                                modules.append(Module(module_type=eve_type))
                slots.append(modules)
        return cls(
            name=fit_name.strip(),
            ship_type=ship_type,
            high_slots=_list_index_or_default(slots, 3, []),
            medium_slots=_list_index_or_default(slots, 2, []),
            low_slots=_list_index_or_default(slots, 1, []),
            rigs=_list_index_or_default(slots, 4, []),
            cargo_bay=cargo_bay,
            drone_bay=drone_bay,
            fighter_bay=fighter_bay,
            fitting_notes=parsed_fitting_notes["fitting_notes"],
        )

    @staticmethod
    def _removeOfflinedModulesMention(lines):
        """Remove /OFFLINE mentions from PYFA when an offlined module is exported
        and add fitting notes when a module is offlined.
        """
        fitting_notes = ""
        eft_lines = []
        for line in lines:
            if "/OFFLINE" in line:
                line = line.replace(" /OFFLINE", "")
                if "," in line:
                    item_name = line.split(",")[0].strip()
                    fitting_notes += "{} is offlined \n".format(item_name)
                else:
                    quantity = line.split()[-1]
                    if "x" in quantity and quantity[1:].isdigit():
                        item_name = line.split(quantity)[0].strip()
                        fitting_notes += "{} is offlined \n".format(item_name)
                    else:
                        item_name = line.strip()
                        fitting_notes += "{} is offlined \n".format(item_name)
            eft_lines.append(line)
        return {"fitting_notes": fitting_notes, "eft_lines": eft_lines}


class _Section:
    """A section within an EFT fitting."""

    def __init__(self):
        self.lines = []

    def is_drone_bay(self):
        types = []
        for line in self.lines:
            if line.startswith("["):
                return False
            if "," in line:
                types.append(_fetch_eve_type(line.split(",")[0].strip()))
            else:
                quantity = line.split()[-1]
                if "x" in quantity and quantity[1:].isdigit():
                    types.append(_fetch_eve_type(line.split(quantity)[0].strip()))
                else:
                    types.append(_fetch_eve_type(line.strip()))
        return all(
            _type is not None and _type.eve_group.eve_category_id == EveCategoryId.DRONE
            for _type in types
        )

    def is_fighter_bay(self):
        types = []
        for line in self.lines:
            if line.startswith("["):
                return False
            if "," in line:
                types.append(_fetch_eve_type(line.split(",")[0].strip()))
            else:
                quantity = line.split()[-1]
                if "x" in quantity and quantity[1:].isdigit():
                    types.append(_fetch_eve_type(line.split(quantity)[0].strip()))
                else:
                    types.append(_fetch_eve_type(line.strip()))
        return all(
            _type is not None
            and _type.eve_group.eve_category_id == EveCategoryId.FIGHTER
            for _type in types
        )

    def parse_bay(self) -> List[Item]:
        items = []
        for line in self.lines:
            quantity = line.split()[-1]
            item_name = line.split(quantity)[0].strip()
            eve_type = _fetch_eve_type(item_name)
            items.append(Item(eve_type=eve_type, quantity=int(quantity.strip("x"))))
        return items

    @classmethod
    def create_from_lines(cls, lines: list) -> Iterable:
        section = cls()
        for line in lines:
            if not line:
                if section.lines:
                    yield section
                    section = cls()
            else:
                section.lines.append(line)
        if section.lines:
            yield section


def _fetch_eve_type(name: str) -> EveType:
    """Fetch eve_type for given name.

    Raises:
    - ValueError: If type does not exist
    """
    try:
        return (
            EveType.objects.filter(enabled_sections=EveType.enabled_sections.dogmas)
            .select_related("eve_group")
            .get(name=name)
        )
    except EveType.DoesNotExist:
        entities = EveEntity.objects.fetch_by_names([name]).filter(
            category=EveEntity.CATEGORY_INVENTORY_TYPE
        )
        if entities.exists():
            entity = entities.first()
            return EveType.objects.select_related("eve_group").get_or_create_esi(
                id=entity.id, enabled_sections=[EveType.Section.DOGMAS]
            )
        raise ValueError("Type with name {name} does not exist.")


def _list_index_or_default(lst: list, index: int, default):
    """Return index from a list or default."""
    try:
        return lst[index]
    except KeyError:
        return default
