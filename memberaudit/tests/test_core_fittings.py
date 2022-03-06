from pathlib import Path

from eveuniverse.models import EveType

from app_utils.testing import NoSocketsTestCase

from ..core.fittings import Fitting, Item, Module
from .testdata.load_eveuniverse import load_eveuniverse


def read_fitting_file(file_name: str) -> str:
    testdata_folder = Path(__file__).parent / "testdata"
    svipul_fitting_file = testdata_folder / file_name
    with svipul_fitting_file.open("r") as fp:
        return fp.read()


def create_fitting(**kwargs):
    params = {
        "name": "Test fitting",
        "ship_type": EveType.objects.get(name="Svipul"),
        "high_slots": [
            Module(
                EveType.objects.get(name="280mm Howitzer Artillery II"),
                position=0,
                charge_type=EveType.objects.get(name="Republic Fleet Phased Plasma S"),
            )
        ],
        "medium_slots": [
            Module(EveType.objects.get(name="Sensor Booster II"), position=0)
        ],
        "low_slots": [
            Module(EveType.objects.get(name="Damage Control II"), position=0)
        ],
        "rigs": [
            Module(
                EveType.objects.get(name="Small Kinetic Shield Reinforcer I"),
                position=0,
            )
        ],
        "drone_bay": [Item(EveType.objects.get(name="Damage Control II"), quantity=5)],
        "cargo_bay": [Item(EveType.objects.get(name="Damage Control II"), quantity=3)],
    }
    params.update(kwargs)
    return Fitting(**params)


class TestFitting(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()

    def test_should_read_fitting_simple(self):
        # given
        svipul_fitting = read_fitting_file("fitting_svipul.txt")
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
    #     svipul_fitting = read_fitting_file("fitting_tristan.txt")
    #     result = Fitting.create_from_eft(svipul_fitting)
    #     print(result)
    #     print([obj.name for obj in result.main_types()])

    def test_should_return_eve_type_ids(self):
        # given
        fit = create_fitting()
        # when
        type_ids = fit.type_ids()
        # then
        self.assertSetEqual(type_ids, {1952, 2977, 34562, 2048, 21924, 31740})

    def test_eft_parser_rountrip(self):
        # given
        self.maxDiff = None
        fitting_text_original = read_fitting_file("fitting_archon.txt")
        fitting = Fitting.create_from_eft(fitting_text_original)
        # when
        fitting_text_generated = fitting.to_eft()
        # then
        self.assertEqual(fitting_text_original, fitting_text_generated)
