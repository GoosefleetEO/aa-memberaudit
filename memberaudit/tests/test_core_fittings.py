# from django.test import TestCase

from app_utils.testing import NoSocketsTestCase

from ..core.fittings import Fitting
from .testdata.factories import create_fitting, create_fitting_text
from .testdata.load_eveuniverse import load_eveuniverse


class TestFitting(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()

    def test_should_return_eve_types(self):
        # given
        fit = create_fitting()
        # when
        types = fit.eve_types()
        # then
        self.assertSetEqual(
            {obj.id for obj in types}, {185, 31716, 3244, 593, 4405, 2873, 2205}
        )

    def test_eft_parser_rountrip_archon_normal(self):
        # given
        self.maxDiff = None
        fitting_text_original = create_fitting_text("fitting_archon.txt")
        fitting, _ = Fitting.create_from_eft(fitting_text_original)
        # when
        fitting_text_generated = fitting.to_eft()
        # then
        self.assertEqual(fitting_text_original, fitting_text_generated)

    def test_eft_parser_rountrip_archon_max(self):
        # given
        self.maxDiff = None
        fitting_text_original = create_fitting_text("fitting_archon_max.txt")
        fitting, _ = Fitting.create_from_eft(fitting_text_original)
        # when
        fitting_text_generated = fitting.to_eft()
        # then
        self.assertEqual(fitting_text_original, fitting_text_generated)

    def test_eft_parser_rountrip_tristan(self):
        # given
        self.maxDiff = None
        fitting_text_original = create_fitting_text("fitting_tristan.txt")
        fitting, _ = Fitting.create_from_eft(fitting_text_original)
        # when
        fitting_text_generated = fitting.to_eft()
        # then
        self.assertEqual(fitting_text_original, fitting_text_generated)

    def test_eft_parser_rountrip_svipul_empty_slots_and_offline(self):
        # given
        self.maxDiff = None
        fitting_text_original = create_fitting_text("fitting_svipul_2.txt")
        fitting, _ = Fitting.create_from_eft(fitting_text_original)
        # when
        fitting_text_generated = fitting.to_eft()
        # then
        self.assertEqual(fitting_text_original, fitting_text_generated)

    def test_eft_parser_rountrip_tengu(self):
        # given
        self.maxDiff = None
        fitting_text_original = create_fitting_text("fitting_tengu.txt")
        fitting, _ = Fitting.create_from_eft(fitting_text_original)
        # print(
        #     ", ".join(map(str, sorted(list([obj.id for obj in fitting.eve_types()]))))
        # )
        # when
        fitting_text_generated = fitting.to_eft()
        # then
        self.assertEqual(fitting_text_original, fitting_text_generated)

    def test_eft_parser_rountrip_empty(self):
        # given
        self.maxDiff = None
        fitting_text_original = create_fitting_text("fitting_empty.txt")
        fitting, _ = Fitting.create_from_eft(fitting_text_original)
        # when
        fitting_text_generated = fitting.to_eft()
        # then
        self.assertEqual(fitting_text_original, fitting_text_generated)

    def test_required_skills(self):
        # given
        fitting_text = create_fitting_text("fitting_tristan.txt")
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
