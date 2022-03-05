from django.contrib.auth.models import Group
from django.db import models
from django.test import TestCase

from allianceauth.eveonline.models import EveCorporationInfo
from app_utils.testing import (
    create_authgroup,
    create_state,
    create_user_from_evecharacter,
)

from ..helpers import clear_users_from_group, filter_groups_available_to_user
from .testdata.load_entities import load_entities


def querysets_pks(qs1: models.QuerySet, qs2: models.QuerySet) -> tuple:
    """Two querysets as set of pks for comparison with assertSetEqual()."""
    qs1_pks = set(qs1.values_list("pk", flat=True))
    qs2_pks = set(qs2.values_list("pk", flat=True))
    return (qs1_pks, qs2_pks)


class TestHelpers(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_entities()
        member_corporation = EveCorporationInfo.objects.get(corporation_id=2001)
        cls.my_state = create_state(
            member_corporations=[member_corporation], priority=200
        )
        cls.normal_group = create_authgroup()
        cls.state_group = create_authgroup(states=[cls.my_state])

    def test_should_include_state_group_for_members(self):
        # given
        user, _ = create_user_from_evecharacter(1001)  # in member corporation
        # when
        result_qs = filter_groups_available_to_user(Group.objects.all(), user)
        # then
        self.assertSetEqual(
            *querysets_pks(
                Group.objects.filter(
                    pk__in=[self.normal_group.pk, self.state_group.pk]
                ),
                result_qs,
            )
        )

    def test_should_not_include_state_group_for_non_members(self):
        # given
        user, _ = create_user_from_evecharacter(1101)  # not in member corporation
        # when
        result_qs = filter_groups_available_to_user(Group.objects.all(), user)
        # then
        self.assertSetEqual(
            *querysets_pks(
                Group.objects.filter(pk__in=[self.normal_group.pk]), result_qs
            )
        )

    def test_should_clear_users_from_group(self):
        # given
        group_1 = create_authgroup()
        group_2 = create_authgroup()
        user_1001, _ = create_user_from_evecharacter(1001)
        user_1001.groups.add(group_1, group_2)
        user_1002, _ = create_user_from_evecharacter(1002)
        user_1002.groups.add(group_1, group_2)
        # when
        clear_users_from_group(group_1)
        # then
        self.assertSetEqual(
            {group_2.pk}, set(user_1001.groups.values_list("pk", flat=True))
        )
        self.assertSetEqual(
            {group_2.pk}, set(user_1002.groups.values_list("pk", flat=True))
        )
