from eveuniverse.models import EveType

from app_utils.testing import NoSocketsTestCase

from ..core.skills import Skill
from .testdata.load_eveuniverse import load_eveuniverse


def create_skill(**kwargs):
    params = {"eve_type": EveType.objects.get(name="Drones"), "level": 1}
    params.update(kwargs)
    return Skill(**params)


class TestSkill(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_eveuniverse()

    def test_can_create_skill_simple(self):
        # when
        drones = EveType.objects.get(name="Drones")
        skill = Skill(eve_type=drones, level=1)
        # then
        self.assertEqual(skill.eve_type, drones)
        self.assertEqual(skill.level, 1)

    def test_can_create_from_eve_type(self):
        # when
        archon = EveType.objects.get(name="125mm Gatling AutoCannon II")
        skills = Skill.create_from_eve_type(archon)
        # then
        skills_str = sorted([str(skill) for skill in skills])
        self.assertListEqual(
            skills_str,
            [
                "Gunnery II",
                "Small Autocannon Specialization I",
                "Small Projectile Turret V",
            ],
        )

    def test_str_1(self):
        # given
        drones = EveType.objects.get(name="Drones")
        skill = Skill(eve_type=drones, level=1)
        # when/then
        self.assertEqual(str(skill), "Drones I")

    def test_str_2(self):
        # given
        light_drone_operations = EveType.objects.get(name="Light Drone Operation")
        # when
        skill = Skill(eve_type=light_drone_operations, level=5)
        # then
        self.assertEqual(str(skill), "Light Drone Operation V")

    def test_compress_skills(self):
        # given
        drones = EveType.objects.get(name="Drones")
        gunnery = EveType.objects.get(name="Gunnery")
        skill_1 = create_skill(eve_type=drones, level=1)
        skill_2 = create_skill(eve_type=gunnery, level=1)
        skill_3 = create_skill(eve_type=drones, level=3)
        skills = [skill_1, skill_2, skill_3]
        # when
        results = Skill.compress_skills(skills)
        # then
        self.assertEqual(len(results), 2)
        self.assertIn(skill_2, results)
        self.assertIn(skill_3, results)
