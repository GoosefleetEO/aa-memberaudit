"""Eve Online Skills"""
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, List, Optional

from eveuniverse.models import EveType

from ..constants import MAP_ARABIC_TO_ROMAN_NUMBERS
from ..constants import EveDogmaAttributeId as AttributeId


@dataclass(frozen=True)
class Skill:
    """A skill in Eve Online."""

    eve_type: EveType
    level: int

    def __str__(self) -> str:
        level_str = MAP_ARABIC_TO_ROMAN_NUMBERS[self.level]
        return f"{self.eve_type.name} {level_str}"

    def __lt__(self, other):
        if self.eve_type != other.eve_type:
            raise TypeError("'<' not supported for skills of different type")
        return self.level < other.level

    def __le__(self, other):
        if self.eve_type != other.eve_type:
            raise TypeError("'<=' not supported for skills of different type")
        return self.level <= other.level

    def __gt__(self, other):
        if self.eve_type != other.eve_type:
            raise TypeError("'>' not supported for skills of different type")
        return self.level > other.level

    def __ge__(self, other):
        if self.eve_type != other.eve_type:
            raise TypeError("'>=' not supported for skills of different type")
        return self.level >= other.level


def compress_skills(skills: List["Skill"]) -> List["Skill"]:
    """Compresses a list of skill by removing redundant skills."""
    skills_map = defaultdict(list)
    for skill in skills:
        skills_map[skill.eve_type.id].append(skill)
    return [max(same_skils) for _, same_skils in skills_map.items()]


def required_skills_from_eve_types(
    eve_types: Iterable[EveType],
) -> Optional[List["Skill"]]:
    """Create list of required skills from eve types."""
    skills_raw = _identify_skills(eve_types)
    skill_types = _gather_skill_types(skills_raw)
    skills = [
        Skill(eve_type=skill_types[type_id], level=level)
        for type_id, level in skills_raw
    ]
    return sorted(skills, key=lambda x: x.eve_type.name)


def _identify_skills(eve_types: Iterable[EveType]) -> list:
    skills_raw = []
    for eve_type in eve_types:
        attributes_raw = eve_type.dogma_attributes.filter(
            eve_dogma_attribute_id__in=[
                AttributeId.REQUIRED_SKILL_1,
                AttributeId.REQUIRED_SKILL_1_LEVEL,
                AttributeId.REQUIRED_SKILL_2,
                AttributeId.REQUIRED_SKILL_2_LEVEL,
                AttributeId.REQUIRED_SKILL_3,
                AttributeId.REQUIRED_SKILL_3_LEVEL,
            ]
        ).values_list("eve_dogma_attribute_id", "value")
        attributes = {int(obj[0]): int(obj[1]) for obj in attributes_raw}
        for skill_id, skill_level_id in {
            AttributeId.REQUIRED_SKILL_1: AttributeId.REQUIRED_SKILL_1_LEVEL,
            AttributeId.REQUIRED_SKILL_2: AttributeId.REQUIRED_SKILL_2_LEVEL,
            AttributeId.REQUIRED_SKILL_3: AttributeId.REQUIRED_SKILL_3_LEVEL,
        }.items():
            if skill_id in attributes and skill_level_id in attributes:
                skills_raw.append((attributes[skill_id], attributes[skill_level_id]))
    return skills_raw


def _gather_skill_types(skills_raw: list) -> dict:
    type_ids = {skill[0] for skill in skills_raw}
    skill_types = {obj.id: obj for obj in EveType.objects.filter(id__in=type_ids)}
    missing_type_ids = type_ids - set(skill_types.keys())
    for type_id in missing_type_ids:
        eve_type, _ = EveType.objects.get_or_create_esi(id=type_id)
        skill_types[type_id] = eve_type
    return skill_types
