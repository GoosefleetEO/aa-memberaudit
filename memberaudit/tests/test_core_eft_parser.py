from pathlib import Path

from eveuniverse.models import EveType

from app_utils.testing import NoSocketsTestCase

from ..core.eft_parser import Fitting, Module
from .testdata.load_eveuniverse import load_eveuniverse


class TestEftParser(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()

    @staticmethod
    def read_fitting_file(file_name: str) -> str:
        testdata_folder = Path(__file__).parent / "testdata"
        svipul_fitting_file = testdata_folder / file_name
        with svipul_fitting_file.open("r") as fp:
            return fp.read()

    def test_should_read_fitting_simple(self):
        # given
        svipul_fitting = self.read_fitting_file("fitting_svipul.txt")
        self.maxDiff = None
        # when
        fitting = Fitting.create_from_eft(svipul_fitting)
        # then
        self.assertEqual(fitting.name, "Svipul - Insta Tank NEW")
        self.assertEqual(fitting.ship_type.name, "Svipul")
        self.assertEqual(
            fitting.low_slots[0],
            Module(EveType.objects.get(name="Damage Control II"), position=0),
        )
        self.assertEqual(
            fitting.low_slots[1],
            Module(EveType.objects.get(name="Gyrostabilizer II"), position=1),
        )
        self.assertEqual(
            fitting.low_slots[2],
            Module(EveType.objects.get(name="Gyrostabilizer II"), position=2),
        )
        self.assertEqual(
            fitting.low_slots[3],
            Module(EveType.objects.get(name="Tracking Enhancer II"), position=3),
        )
        self.assertEqual(
            fitting.medium_slots[0],
            Module(EveType.objects.get(name="Sensor Booster II"), position=0),
        )
        self.assertEqual(
            fitting.medium_slots[1],
            Module(EveType.objects.get(name="Sensor Booster II"), position=1),
        )
        self.assertEqual(
            fitting.medium_slots[2],
            Module(EveType.objects.get(name="Warp Disruptor II"), position=2),
        )
        self.assertEqual(
            fitting.medium_slots[3],
            Module(
                EveType.objects.get(name="5MN Y-T8 Compact Microwarpdrive"), position=3
            ),
        )
        self.assertEqual(
            fitting.high_slots[0],
            Module(
                EveType.objects.get(name="280mm Howitzer Artillery II"),
                position=0,
                charge_type=EveType.objects.get(name="Republic Fleet Phased Plasma S"),
            ),
        )
        self.assertEqual(
            fitting.high_slots[1],
            Module(
                EveType.objects.get(name="280mm Howitzer Artillery II"),
                position=1,
                charge_type=EveType.objects.get(name="Republic Fleet Phased Plasma S"),
            ),
        )
        self.assertEqual(
            fitting.high_slots[2],
            Module(
                EveType.objects.get(name="280mm Howitzer Artillery II"),
                position=2,
                charge_type=EveType.objects.get(name="Republic Fleet Phased Plasma S"),
            ),
        )
        self.assertEqual(
            fitting.high_slots[3],
            Module(
                EveType.objects.get(name="280mm Howitzer Artillery II"),
                position=3,
                charge_type=EveType.objects.get(name="Republic Fleet Phased Plasma S"),
            ),
        )
        self.assertEqual(
            fitting.rigs[0],
            Module(
                EveType.objects.get(name="Small Targeting System Subcontroller II"),
                position=0,
            ),
        )
        self.assertEqual(
            fitting.rigs[1],
            Module(
                EveType.objects.get(name="Small Thermal Shield Reinforcer I"),
                position=1,
            ),
        )
        self.assertEqual(
            fitting.rigs[2],
            Module(
                EveType.objects.get(name="Small Kinetic Shield Reinforcer I"),
                position=2,
            ),
        )

    # def test_should_read_fitting_with_drones(self):
    #     svipul_fitting = self.read_fitting_file("fitting_tristan.txt")
    #     result = Fitting.create_from_eft(svipul_fitting)
    #     print(result)
    #     print([obj.name for obj in result.main_types()])
