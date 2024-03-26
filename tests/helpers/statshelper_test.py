import unittest

from db.sm5 import SM5Game, SM5Stats
from helpers.statshelper import count_zaps, get_sm5_kd_ratio, get_sm5_score_components
from tests.helpers.environment import setup_test_database, ENTITY_ID_1, ENTITY_ID_2, get_sm5_game_id, \
    teardown_test_database, create_destroy_base_event, add_entity, get_red_team


class TestStatsHelper(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await setup_test_database()

    async def asyncTearDown(self):
        await teardown_test_database()

    async def test_count_zaps(self):
        game = await SM5Game.filter(id=get_sm5_game_id()).first()
        zaps = await count_zaps(game, ENTITY_ID_1, ENTITY_ID_2)
        self.assertEqual(3, zaps)

    async def test_get_sm5_score_components(self):
        game = await SM5Game.filter(id=get_sm5_game_id()).first()
        await game.events.add(await create_destroy_base_event(time_millis=10000,
                                                              destroying_entity_id=ENTITY_ID_1,
                                                              base_entity_str="@red_base"))
        await game.events.add(await create_destroy_base_event(time_millis=20000,
                                                              destroying_entity_id=ENTITY_ID_1,
                                                              base_entity_str="@reactor"))
        entity_start, entity_end = await add_entity(entity_id=ENTITY_ID_1, team=get_red_team())

        stats = SM5Stats(
            missiled_opponent=3,
            shot_opponent=5,
            nukes_detonated=7,
            shot_team=11,
            missiled_team=13,
            times_zapped=17,
            times_missiled=23,
        )

        self.assertDictEqual({
            "Missiles": 1500,
            "Zaps": 500,
            "Bases": 2002,
            "Nukes": 3500,
            "Zap own team": -1100,
            "Missiled own team": -6500,
            "Got zapped": -340,
            "Got missiled": -2300,
        }, await get_sm5_score_components(game, stats, entity_start))

    async def test_get_kd_ratio(self):
        stats = SM5Stats(
            shot_opponent=10,
            times_zapped=2,
        )

        self.assertEqual(5.0, get_sm5_kd_ratio(stats))

    async def test_get_kd_ratio_never_zapped(self):
        stats = SM5Stats(
            shot_opponent=10,
            times_zapped=0,
        )

        self.assertEqual(1.0, get_sm5_kd_ratio(stats))


if __name__ == '__main__':
    unittest.main()
