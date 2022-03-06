from django.test import TestCase
from eveuniverse.models import EveUniverseEntityModel
from eveuniverse.tools.testdata import ModelSpec, create_testdata

from . import eveuniverse_test_data_filename


class CreateEveUniverseTestData(TestCase):
    def test_create_testdata(self):
        testdata_spec = [
            ModelSpec("EveAncestry", ids=[11]),
            ModelSpec("EveBloodline", ids=[1]),
            ModelSpec("EveFaction", ids=[500001]),
            ModelSpec("EveRace", ids=[1]),
            ModelSpec("EveSolarSystem", ids=[30000142, 30004984, 30001161, 30002537]),
            ModelSpec(
                "EveType",
                ids=[
                    2,
                    5,
                    23,
                    603,
                    1376,
                    16159,
                    20185,
                    24311,
                    24312,
                    24313,
                    24314,
                    35832,
                    35835,
                    52678,
                ],
            ),
            ModelSpec(
                "EveType",
                ids=[
                    519,  # Gyrostabilizer II
                    2048,  # Damage Control II
                    1999,  # Tracking Enhancer II
                    1952,  # Sensor Booster II
                    3244,  # Warp Disruptor II
                    5973,  # 5MN Y-T8 Compact Microwarpdrive
                    2977,  # 280mm Howitzer Artillery II
                    21924,  # Republic Fleet Phased Plasma S
                    31328,  # Small Targeting System Subcontroller II
                    31740,  # Small Thermal Shield Reinforcer I
                    31752,  # Small Kinetic Shield Reinforcer I
                    34562,  # Svipul
                    19540,  # High-grade Snake Alpha
                    19551,  # High-grade Snake Beta
                    19553,  # High-grade Snake Gamma
                ],
                enabled_sections=[EveUniverseEntityModel.LOAD_DOGMAS],
            ),
        ]
        create_testdata(testdata_spec, eveuniverse_test_data_filename())
