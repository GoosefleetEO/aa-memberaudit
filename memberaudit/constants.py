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
    SUBSYSTEM = 32
    STRUCTURE = 65


class EveGroupId(IntEnum):
    CYBERIMPLANT = 300
    BOOSTER = 303


class EveTypeId(IntEnum):
    SOLAR_SYSTEM = 5


class EveDogmaAttributeId(IntEnum):
    REQUIRED_SKILL_1 = 182
    REQUIRED_SKILL_2 = 183
    REQUIRED_SKILL_3 = 184
    REQUIRED_SKILL_1_LEVEL = 277
    REQUIRED_SKILL_2_LEVEL = 278
    REQUIRED_SKILL_3_LEVEL = 279


class EveDogmaEffectId(IntEnum):
    LO_POWER = 11
    HI_POWER = 12
    MED_POWER = 13
    RIG_SLOT = 2663
    SUB_SYSTEM = 3772


MAP_ARABIC_TO_ROMAN_NUMBERS = {0: "-", 1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}

DATETIME_FORMAT = "%Y-%b-%d %H:%M"
