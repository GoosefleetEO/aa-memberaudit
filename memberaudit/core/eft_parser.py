from dataclasses import dataclass
from typing import List

from eveuniverse.models import EveEntity, EveType

from ..constants import EveCategoryId


@dataclass
class Module:
    """A ship module used in a fitting."""

    name: str
    charge: str
    position: int


@dataclass
class Item:
    """An item used in a fitting."""

    name: str
    quantity: int


@dataclass
class Fitting:
    """A fitting for a ship in Eve Online."""

    ship_type: str
    name: str
    modules: list
    cargo: list
    drone_bay: list
    fighter_bay: list
    fitting_notes: str

    def __str__(self) -> str:
        return f"{self.name}"

    def main_types(self) -> List[EveType]:
        """List of types used in the fitting. Does not include cargo."""
        type_names = {module.name for module in self.modules} | {self.ship_type}
        types = [_fetch_eve_type(type_name) for type_name in type_names]
        return types

    @classmethod
    def create_from_eft(cls, eft_text: str) -> dict:
        """Parse fitting in EFT format"""
        eft_lines = eft_text.strip().splitlines()
        parsed_fitting_notes = cls._removeOfflinedModulesMention(eft_lines)
        sections = [
            section
            for section in cls._import_section_iter(parsed_fitting_notes["eft_lines"])
        ]
        modules = []
        cargo = []
        drone_bay = []
        fighter_bay = []
        ship_type = ""
        fit_name = ""
        for section in sections:
            counter = 0
            if section.is_drone_bay():
                for line in section.lines:
                    quantity = line.split()[-1]
                    item_name = line.split(quantity)[0].strip()
                    drone_bay.append(
                        Item(name=item_name, quantity=int(quantity.strip("x")))
                    )
            elif section.is_fighter_bay():
                for line in section.lines:
                    quantity = line.split()[-1]
                    item_name = line.split(quantity)[0].strip()
                    fighter_bay.append(
                        Item(name=item_name, quantity=int(quantity.strip("x")))
                    )
            else:
                for line in section.lines:
                    if line.startswith("["):
                        if "," in line:
                            ship_type, fit_name = line[1:-1].split(",")
                            continue

                        if "empty" in line.strip("[]").lower():
                            continue
                    else:
                        if "," in line:
                            module, charge = line.split(",")
                            modules.append(
                                Module(
                                    name=module, charge=charge.strip(), position=counter
                                )
                            )
                        else:
                            quantity = line.split()[
                                -1
                            ]  # Quantity will always be the last element, if it is there.
                            if "x" in quantity and quantity[1:].isdigit():
                                item_name = line.split(quantity)[0].strip()
                                cargo.append(
                                    Item(
                                        name=item_name,
                                        quantity=int(quantity.strip("x")),
                                    )
                                )
                            else:
                                modules.append(
                                    Module(
                                        name=line.strip(), charge="", position=counter
                                    )
                                )
                    counter += 1
        result = {
            "ship_type": ship_type,
            "name": fit_name,
            "modules": modules,
            "cargo": cargo,
            "drone_bay": drone_bay,
            "fighter_bay": fighter_bay,
            "fitting_notes": parsed_fitting_notes["fitting_notes"],
        }
        return cls(**result)

    def _import_section_iter(lines):
        section = _Section()
        for line in lines:
            if not line:
                if section.lines:
                    yield section
                    section = _Section()
            else:
                section.lines.append(line)
        if section.lines:
            yield section

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
