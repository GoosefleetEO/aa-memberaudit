from enum import IntEnum


class EveCategoryId(IntEnum):
    STATION = 3
    SHIP = 6
    MODULE = 7
    CHARGE = 8
    BLUEPRINT = 9
    SKILL = 16
    DRONE = 18
    IMPLANT = 20
    FIGHTER = 87
    STRUCTURE = 65


class EveTypeId(IntEnum):
    SOLAR_SYSTEM = 5


class EveDogmaAttributeId(IntEnum):
    REQUIRED_SKILL_1 = 182
    REQUIRED_SKILL_2 = 183
    REQUIRED_SKILL_3 = 184
    REQUIRED_SKILL_1_LEVEL = 277
    REQUIRED_SKILL_2_LEVEL = 278
    REQUIRED_SKILL_3_LEVEL = 279
