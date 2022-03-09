from eveuniverse.models import EveType

from app_utils.testing import NoSocketsTestCase

from ..core.eft_parser import _EveTypes, create_fitting_from_eft
from .testdata.load_eveuniverse import load_eveuniverse
from .utils import read_fitting_file


class TestFitting(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()

    def test_should_create_fitting(self):
        # given
        fitting_text = read_fitting_file("fitting_tristan.txt")
        # when
        fitting = create_fitting_from_eft(fitting_text)
        # then
        self.assertEqual(fitting.name, "Tristan - Standard Kite (cap stable)")
        self.assertEqual(fitting.ship_type.name, "Tristan")
        self.assertEqual(
            fitting.low_slots[0].module_type.name, "Nanofiber Internal Structure II"
        )
        self.assertEqual(
            fitting.low_slots[1].module_type.name, "Drone Damage Amplifier II"
        )
        self.assertEqual(
            fitting.low_slots[2].module_type.name, "Drone Damage Amplifier II"
        )

        self.assertEqual(
            fitting.medium_slots[0].module_type.name,
            "5MN Cold-Gas Enduring Microwarpdrive",
        )
        self.assertEqual(
            fitting.medium_slots[1].module_type.name,
            "Medium Azeotropic Restrained Shield Extender",
        )
        self.assertEqual(fitting.medium_slots[2].module_type.name, "Warp Disruptor II")
        self.assertTrue(fitting.medium_slots[2].is_offline)

        self.assertEqual(
            fitting.high_slots[0].module_type.name, "125mm Gatling AutoCannon II"
        )
        self.assertEqual(fitting.high_slots[0].charge_type.name, "EMP S")
        self.assertEqual(
            fitting.high_slots[1].module_type.name, "125mm Gatling AutoCannon II"
        )
        self.assertEqual(fitting.high_slots[1].charge_type.name, "EMP S")
        self.assertIsNone(fitting.high_slots[2])

        self.assertEqual(
            fitting.rig_slots[0].module_type.name, "Small Capacitor Control Circuit I"
        )
        self.assertEqual(
            fitting.rig_slots[1].module_type.name, "Small Polycarbon Engine Housing I"
        )
        self.assertEqual(
            fitting.rig_slots[2].module_type.name, "Small EM Shield Reinforcer I"
        )

        self.assertEqual(fitting.drone_bay[0].item_type.name, "Acolyte II")
        self.assertEqual(fitting.drone_bay[0].quantity, 5)
        self.assertEqual(fitting.drone_bay[1].item_type.name, "Warrior II")
        self.assertEqual(fitting.drone_bay[1].quantity, 3)


class TestEveTypes(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()

    def test_should_create_from_names(self):
        # given
        drones = EveType.objects.get(name="Drones")
        gunnery = EveType.objects.get(name="Gunnery")
        # when
        eve_types = _EveTypes.create_from_names(["Drones", "Gunnery"])
        # then
        self.assertEqual(eve_types.from_name("Drones"), drones)
        self.assertEqual(eve_types.from_name("Gunnery"), gunnery)
