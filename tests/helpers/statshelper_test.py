import unittest

from db.game import EntityStarts
from db.sm5 import SM5Game, SM5Stats
from db.types import Team
from helpers.statshelper import count_zaps, get_sm5_kd_ratio, get_sm5_score_components, \
    get_sm5_single_player_score_graph_data, get_sm5_single_team_score_graph_data, get_sm5_team_score_graph_data, \
    get_sm5_gross_positive_score, get_points_per_minute
from tests.helpers.environment import setup_test_database, ENTITY_ID_1, ENTITY_ID_2, get_sm5_game_id, \
    teardown_test_database, create_destroy_base_event, add_entity, get_red_team, get_green_team, add_sm5_score, \
    create_award_base_event


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
        await game.events.add(await create_award_base_event(time_millis=20000,
                                                            destroying_entity_id=ENTITY_ID_1,
                                                            base_entity_str="@yellow_base"))
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
            "Bases": 3003,
            "Nukes": 3500,
            "Zap own team": -1100,
            "Missiled own team": -6500,
            "Got zapped": -340,
            "Got missiled": -2300,
        }, await get_sm5_score_components(game, stats, entity_start))

    def test_get_sm5_gross_positive_score(self):
        net_score = get_sm5_gross_positive_score({
            "Zaps": 3000,
            "Forgot to take out the trash": -200,
            "Nukes": 500,
            "Got missiled": -400,
        })

        # The final score should only be the positive parts (3000 and 500).
        self.assertEqual(3500, net_score)

    async def test_get_points_per_minute(self):
        entity, entity_end = await add_entity(ENTITY_ID_1, team=get_red_team(), end_time_millis=900000, score=3000)

        points_per_minute = get_points_per_minute(entity_end)

        # 3000 points in 15 minutes.
        self.assertEqual(200, points_per_minute)

    async def test_get_points_per_minute_zero_time(self):
        entity, entity_end = await add_entity(ENTITY_ID_1, team=get_red_team(), end_time_millis=0, score=3000)

        points_per_minute = get_points_per_minute(entity_end)

        self.assertEqual(0, points_per_minute)


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

    async def test_get_sm5_single_player_score_graph_data(self):
        entity1 = await self.create_score_test_scenario()

        game = await SM5Game.filter(id=get_sm5_game_id()).first()
        scores = await get_sm5_single_player_score_graph_data(game, entity1.id)

        self.assertEqual([
            # 00:00
            0, 0, 0, 0, 100, 100, 100, 100, 100, 100,
            # 05:00
            100, 100, 100, 100, 500, 500, 500, 500, 500, 500,
            # 10:00
            500, 500, 500, 500, 500, 500, 500, 500, 500, 500, 500], scores)

    async def test_get_sm5_single_team_score_graph_data(self):
        await self.create_score_test_scenario()

        game = await SM5Game.filter(id=get_sm5_game_id()).first()
        scores = await get_sm5_single_team_score_graph_data(game, Team.RED)

        self.assertEqual([
            # 00:00
            0, 0, 0, 0, 100, 100, 100, 100, 100, 100,
            # 05:00
            400, 400, 400, 400, 800, 800, 800, 800, 800, 800,
            # 10:00
            800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800], scores)

    async def test_get_sm5_team_score_graph_data(self):
        await self.create_score_test_scenario()

        game = await SM5Game.filter(id=get_sm5_game_id()).first()
        scores = await get_sm5_team_score_graph_data(game, [Team.RED, Team.GREEN])

        self.assertEqual({
            Team.RED: [
                # 00:00
                0, 0, 0, 0, 100, 100, 100, 100, 100, 100,
                # 05:00
                400, 400, 400, 400, 800, 800, 800, 800, 800, 800,
                # 10:00
                800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800],
            Team.GREEN: [
                # 00:00
                0, 0, 0, 0, 0, 0, 0, 200, 200, 200,
                # 05:00
                200, 200, 200, 200, 200, 200, 200, 200, 200, 200,
                # 10:00
                200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200]},
            scores)

    async def create_score_test_scenario(self) -> EntityStarts:
        game = await SM5Game.filter(id=get_sm5_game_id()).first()

        entity1, entity_end1 = await add_entity(entity_id="@LoggedIn", team=get_red_team())
        entity2, entity_end2 = await add_entity(entity_id="@Member", team=get_green_team())
        entity3, entity_end3 = await add_entity(entity_id="NotLoggedIn", team=get_red_team())

        # At 01:40: 100 points.
        await add_sm5_score(game, time_millis=100000, entity=entity1, old_score=0, score=100)
        # At 03:20: 200 points for green team.
        await add_sm5_score(game, time_millis=200000, entity=entity2, old_score=0, score=200)
        # At 05:00: 300 points for entity3.
        await add_sm5_score(game, time_millis=300000, entity=entity3, old_score=0, score=300)
        # At 06:40: 500 points.
        await add_sm5_score(game, time_millis=400000, entity=entity1, old_score=100, score=500)
        # At 16:40 (Irrelevant, past end of the game)
        await add_sm5_score(game, time_millis=1000000, entity=entity1, old_score=500, score=600)

        return entity1


if __name__ == '__main__':
    unittest.main()
