"""Eve Online Fittings"""
from dataclasses import dataclass
from typing import Iterable, List, Optional, Set

from eveuniverse.models import EveEntity, EveType

from ..constants import EveCategoryId


@dataclass
class Module:
    """A ship module used in a fitting."""

    module_type: EveType
    charge_type: EveType = None

    def type_ids(self) -> Set[int]:
        """Type IDs used in this module."""
        ids = {self.module_type.id}
        if self.charge_type:
            ids.add(self.charge_type.id)
        return ids

    def to_eft(self) -> str:
        """Convert to EFT format."""
        text = self.module_type.name
        if self.charge_type:
            text += f", {self.charge_type.name}"
        return text


@dataclass
class Item:
    """An item used in a fitting."""

    eve_type: EveType
    quantity: int

    def type_ids(self) -> Set[int]:
        """Type IDs used in this module."""
        return {self.eve_type.id}

    def to_eft(self) -> str:
        """Convert to EFT format."""
        return f"{self.eve_type.name} x{self.quantity}"


@dataclass
class Skill:
    """A skill in Eve Online."""

    eve_type: EveType
    level: int


@dataclass
class Fitting:
    """A fitting for a ship in Eve Online."""

    name: str
    ship_type: EveType
    high_slots: List[Optional[Module]] = None
    medium_slots: List[Optional[Module]] = None
    low_slots: List[Optional[Module]] = None
    rigs: List[Optional[Module]] = None
    cargo_bay: List[Item] = None
    drone_bay: List[Item] = None
    fighter_bay: List[Item] = None
    fitting_notes: str = ""

    def __post_init__(self):
        if not self.high_slots:
            self.high_slots = []
        if not self.medium_slots:
            self.medium_slots = []
        if not self.low_slots:
            self.low_slots = []
        if not self.rigs:
            self.rigs = []
        if not self.cargo_bay:
            self.cargo_bay = []
        if not self.drone_bay:
            self.drone_bay = []
        if not self.fighter_bay:
            self.fighter_bay = []

    def __str__(self) -> str:
        return f"{self.name}"

    @property
    def modules(self) -> List[EveType]:
        """All fitted modules."""
        return self.high_slots + self.medium_slots + self.low_slots + self.rigs

    def type_ids(self, include_cargo=True) -> Set[int]:
        """Types of all modules and items."""
        objs = self.modules + self.drone_bay + self.fighter_bay
        if include_cargo:
            objs += self.cargo_bay
        type_ids = {self.ship_type.id}
        for obj in [x for x in objs if x]:
            type_ids |= {type_id for type_id in obj.type_ids()}
        return type_ids

    def required_skills(self) -> List[Skill]:
        """Skills required to fly this fitting."""
        ...

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
                            continue

                        if "empty" in line.strip("[]").lower():
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
