from eveuniverse.models import EveType

from app_utils.testing import NoSocketsTestCase

from ..core.skills import Skill
from .testdata.load_eveuniverse import load_eveuniverse


class TestSkill(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_eveuniverse()

    def test_can_create_skill_simple_1(self):
        # when
        drones = EveType.objects.get(name="Drones")
        skill = Skill(eve_type=drones, level=1)
        # then
        self.assertEqual(skill.eve_type, drones)
        self.assertEqual(skill.level, 1)
        self.assertListEqual(skill.required_skills, [])

    def test_can_create_skill_simple_2(self):
        # when
        drones = EveType.objects.get(name="Drones")
        skill = Skill.create(eve_type=drones, level=1)
        # then
        self.assertEqual(skill.eve_type, drones)
        self.assertEqual(skill.level, 1)
        self.assertListEqual(skill.required_skills, [])

    def test_str_1(self):
        # given
        drones = EveType.objects.get(name="Drones")
        skill = Skill.create(eve_type=drones, level=1)
        # when/then
        self.assertEqual(str(skill), "Drones I")

    def test_str_2(self):
        # given
        light_drone_operations = EveType.objects.get(name="Light Drone Operation")
        # when
        skill = Skill.create(eve_type=light_drone_operations, level=5)
        # then
        self.assertEqual(str(skill), "Light Drone Operation V [Drones I]")

    def test_can_create_skill_with_required_skills(self):
        # given
        drones = EveType.objects.get(name="Drones")
        light_drone_operations = EveType.objects.get(name="Light Drone Operation")
        # when
        skill = Skill.create(eve_type=light_drone_operations, level=5)
        # then
        self.assertEqual(skill.eve_type, light_drone_operations)
        self.assertEqual(skill.level, 5)
        self.assertListEqual(skill.required_skills, [Skill(eve_type=drones, level=1)])

    def test_can_create_required_skills(self):
        # given
        drones = EveType.objects.get(name="Drones")
        light_drone_operations = EveType.objects.get(name="Light Drone Operation")
        amarr_drone_specialization = EveType.objects.get(
            name="Amarr Drone Specialization"
        )
        acolyte_ii = EveType.objects.get(name="Acolyte II")
        # when
        skills = Skill.create_required_skills(eve_type=acolyte_ii)
        # then
        self.assertEqual(
            Skill(amarr_drone_specialization, 1, [Skill(drones, 5)]), skills[0]
        )
        self.assertEqual(Skill(drones, 5), skills[1])
        self.assertEqual(
            Skill(light_drone_operations, 5, [Skill(drones, 1)]), skills[2]
        )
