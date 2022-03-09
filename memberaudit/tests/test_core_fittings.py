from eveuniverse.models import EveType

from app_utils.testing import NoSocketsTestCase

from ..core.fittings import Fitting, Item, Module
from .testdata.load_eveuniverse import load_eveuniverse
from .utils import read_fitting_file


def create_fitting(**kwargs):
    params = {
        "name": "Test fitting",
        "ship_type": EveType.objects.get(name="Svipul"),
        "high_slots": [
            Module(
                EveType.objects.get(name="280mm Howitzer Artillery II"),
                charge_type=EveType.objects.get(name="Republic Fleet Phased Plasma S"),
            ),
            None,
        ],
        "medium_slots": [Module(EveType.objects.get(name="Sensor Booster II")), None],
        "low_slots": [Module(EveType.objects.get(name="Damage Control II")), None],
        "rig_slots": [
            Module(
                EveType.objects.get(name="Small Kinetic Shield Reinforcer I"),
            ),
            None,
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

    # def test_should_read_fitting_with_drones(self):
    #     svipul_fitting = read_fitting_file("fitting_tristan.txt")
    #     result = Fitting.create_from_eft(svipul_fitting)
    #     print(result)
    #     print([obj.name for obj in result.main_types()])

    def test_should_return_eve_types(self):
        # given
        fit = create_fitting()
        # when
        types = fit.eve_types()
        # then
        self.assertSetEqual(
            {obj.id for obj in types}, {1952, 2977, 34562, 2048, 21924, 31740}
        )

    def test_eft_parser_rountrip_archon_normal(self):
        # given
        self.maxDiff = None
        fitting_text_original = read_fitting_file("fitting_archon.txt")
        fitting, _ = Fitting.create_from_eft(fitting_text_original)
        # when
        fitting_text_generated = fitting.to_eft()
        # then
        self.assertEqual(fitting_text_original, fitting_text_generated)

    def test_eft_parser_rountrip_archon_max(self):
        # given
        self.maxDiff = None
        fitting_text_original = read_fitting_file("fitting_archon_max.txt")
        fitting, _ = Fitting.create_from_eft(fitting_text_original)
        # when
        fitting_text_generated = fitting.to_eft()
        # then
        self.assertEqual(fitting_text_original, fitting_text_generated)

    def test_eft_parser_rountrip_tristan(self):
        # given
        self.maxDiff = None
        fitting_text_original = read_fitting_file("fitting_tristan.txt")
        fitting, _ = Fitting.create_from_eft(fitting_text_original)
        # when
        fitting_text_generated = fitting.to_eft()
        # then
        self.assertEqual(fitting_text_original, fitting_text_generated)

    def test_eft_parser_rountrip_svipul_empty_slots_and_offline(self):
        # given
        self.maxDiff = None
        fitting_text_original = read_fitting_file("fitting_svipul_2.txt")
        fitting, _ = Fitting.create_from_eft(fitting_text_original)
        # when
        fitting_text_generated = fitting.to_eft()
        # then
        self.assertEqual(fitting_text_original, fitting_text_generated)

    def test_required_skills(self):
        # given
        fitting_text = read_fitting_file("fitting_tristan.txt")
        fitting, _ = Fitting.create_from_eft(fitting_text)
        # when
        skills = fitting.required_skills()
        # then
        skills_str = sorted([str(skill) for skill in skills])
        self.assertListEqual(
            skills_str,
            [
                "Amarr Drone Specialization I",
                "Drones V",
                "Gallente Frigate I",
                "Gunnery II",
                "High Speed Maneuvering I",
                "Hull Upgrades II",
                "Light Drone Operation V",
                "Minmatar Drone Specialization I",
                "Propulsion Jamming II",
                "Shield Upgrades I",
                "Small Autocannon Specialization I",
                "Small Projectile Turret V",
                "Weapon Upgrades IV",
            ],
        )
