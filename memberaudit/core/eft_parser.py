from dataclasses import dataclass
from typing import Iterable, List

from django.db import models
from eveuniverse.models import EveEntity, EveType

from ..constants import EveCategoryId


@dataclass
class Module:
    """A ship module used in a fitting."""

    module_type: EveType
    position: int
    charge_type: EveType = None


@dataclass
class Item:
    """An item used in a fitting."""

    eve_type: EveType
    quantity: int


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
    high_slots: List[Module]
    medium_slots: List[Module]
    low_slots: List[Module]
    rigs: List[Module]
    cargo: List[Item]
    drone_bay: List[Item]
    fighter_bay: List[Item]
    fitting_notes: str

    def __str__(self) -> str:
        return f"{self.name}"

    @property
    def modules(self) -> List[EveType]:
        """All fitted modules."""
        return self.high_slots + self.medium_slots + self.low_slots + self.rigs

    def main_types(self) -> models.QuerySet:
        """Main types used in the fitting. Does not include cargo."""
        type_ids = {module.eve_type.id for module in self.modules} | {self.ship_type.id}
        return EveType.objects.filter(id__in=type_ids)

    def required_skills(self) -> List[Skill]:
        """Skills required to fly this fitting."""
        ...

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
        cargo = []
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
                counter = 0
                modules = []
                for line in section.lines:
                    if line.startswith("["):
                        if "," in line:
                            ship_type_name, fit_name = line[1:-1].split(",")
                            ship_type = _fetch_eve_type(ship_type_name)
                            continue

                        if "empty" in line.strip("[]").lower():
                            continue
                    else:
                        if "," in line:
                            module_name, charge_name = line.split(",")
                            module_type = _fetch_eve_type(module_name)
                            charge_type = _fetch_eve_type(charge_name.strip())
                            modules.append(
                                Module(
                                    module_type=module_type,
                                    position=counter,
                                    charge_type=charge_type,
                                )
                            )
                        else:
                            quantity = line.split()[
                                -1
                            ]  # Quantity will always be the last element, if it is there.
                            if "x" in quantity and quantity[1:].isdigit():
                                item_name = line.split(quantity)[0].strip()
                                eve_type = _fetch_eve_type(item_name)
                                cargo.append(
                                    Item(
                                        eve_type=eve_type,
                                        quantity=int(quantity.strip("x")),
                                    )
                                )
                            else:
                                module_name = line.strip()
                                eve_type = _fetch_eve_type(module_name)
                                modules.append(
                                    Module(module_type=eve_type, position=counter)
                                )
                    counter += 1
                slots.append(modules)
        return cls(
            name=fit_name.strip(),
            ship_type=ship_type,
            high_slots=_list_index_or_default(slots, 3, []),
            medium_slots=_list_index_or_default(slots, 2, []),
            low_slots=_list_index_or_default(slots, 1, []),
            rigs=_list_index_or_default(slots, 4, []),
            cargo=cargo,
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
        return EveType.objects.select_related("eve_group").get(name=name)
    except EveType.DoesNotExist:
        entities = EveEntity.objects.fetch_by_names([name]).filter(
            category=EveEntity.CATEGORY_INVENTORY_TYPE
        )
        if entities.exists():
            entity = entities.first()
            return EveType.objects.select_related("eve_group").get_or_create_esi(
                id=entity.id
            )
        raise ValueError("Type with name {name} does not exist.")


def _list_index_or_default(lst: list, index: int, default):
    """Return index from a list or default."""
    try:
        return lst[index]
    except KeyError:
        return default
