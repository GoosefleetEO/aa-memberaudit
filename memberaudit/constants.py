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


class EveGroupId(IntEnum):
    CHARACTER = 1
    CORPORATION = 2
    SOLAR_SYSTEM = 5
    STATION = 15
    ALLIANCE = 32


class EveTypeId(IntEnum):
    SOLAR_SYSTEM = 5
