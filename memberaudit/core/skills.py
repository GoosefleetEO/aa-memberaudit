"""Eve Online Skills"""
from dataclasses import dataclass, field
from typing import List, Optional

from eveuniverse.models import EveType

from ..constants import MAP_ARABIC_TO_ROMAN_NUMBERS
from ..constants import EveDogmaAttributeId as AttributeId


@dataclass(frozen=True)
class Skill:
    """A skill in Eve Online."""

    eve_type: EveType
    level: int
    required_skills: List["Skill"] = field(default_factory=list)

    def __str__(self) -> str:
        if self.required_skills:
            skills_str = [str(obj) for obj in self.required_skills]
            required_skills = f" [{', '.join(skills_str)}]"
        else:
            required_skills = ""
        level_str = MAP_ARABIC_TO_ROMAN_NUMBERS[self.level]
        return f"{self.eve_type.name} {level_str}{required_skills}"

    @classmethod
    def create(cls, eve_type: EveType, level: int) -> "Skill":
        """Create new skill."""
        required_skills = cls.create_required_skills(eve_type)
        return cls(eve_type=eve_type, level=level, required_skills=required_skills)

    @classmethod
    def create_required_skills(cls, eve_type: EveType) -> Optional[List["Skill"]]:
        """Create required skills from given type."""

        def _create_skill_from_attributes(
            attributes: dict, skill_id: int, skill_level_id: int
        ):
            if skill_id in attributes and skill_level_id in attributes:
                skill_type_id = attributes[skill_id]
                skill_level = attributes[skill_level_id]
                eve_type, _ = EveType.objects.get_or_create_esi(id=skill_type_id)
                return Skill.create(eve_type=eve_type, level=skill_level)
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
