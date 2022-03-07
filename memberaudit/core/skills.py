"""Eve Online Skills"""
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Optional

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

    @classmethod
    def create_from_eve_type(cls, eve_type: EveType) -> Optional[List["Skill"]]:
        """Create required skills from given type."""

        def _create_skill_from_attributes(
            attributes: dict, skill_id: int, skill_level_id: int
        ):
            if skill_id in attributes and skill_level_id in attributes:
                skill_type_id = attributes[skill_id]
                skill_level = attributes[skill_level_id]
                eve_type, _ = EveType.objects.get_or_create_esi(id=skill_type_id)
                return Skill(eve_type=eve_type, level=skill_level)
            return None

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
        skills = []
        for skill_id, skill_level_id in {
            AttributeId.REQUIRED_SKILL_1: AttributeId.REQUIRED_SKILL_1_LEVEL,
            AttributeId.REQUIRED_SKILL_2: AttributeId.REQUIRED_SKILL_2_LEVEL,
            AttributeId.REQUIRED_SKILL_3: AttributeId.REQUIRED_SKILL_3_LEVEL,
        }.items():
            skill = _create_skill_from_attributes(attributes, skill_id, skill_level_id)
            if skill:
                skills.append(skill)
        return sorted(skills, key=lambda x: x.eve_type.name)

    @classmethod
    def compress_skills(cls, skills: List["Skill"]) -> List["Skill"]:
        """Compresses a list of skill by removing redundant skills."""
        skills_map = defaultdict(list)
        for skill in skills:
            skills_map[skill.eve_type.id].append(skill)
        return [max(same_skils) for _, same_skils in skills_map.items()]
