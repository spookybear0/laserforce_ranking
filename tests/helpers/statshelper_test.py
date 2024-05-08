import unittest

from db.game import EntityStarts
from db.laserball import LaserballGame
from db.sm5 import SM5Game, SM5Stats
from db.types import Team
from helpers.statshelper import count_zaps, get_sm5_kd_ratio, get_sm5_score_components, \
    get_sm5_single_player_score_graph_data, get_sm5_single_team_score_graph_data, get_sm5_team_score_graph_data, \
    get_sm5_gross_positive_score, get_points_per_minute, count_blocks, count_missiles, get_points_scored
from tests.helpers.environment import setup_test_database, ENTITY_ID_1, ENTITY_ID_2, ENTITY_ID_3, get_sm5_game_id, \
    teardown_test_database, create_destroy_base_event, add_entity, get_red_team, get_green_team, add_sm5_score, \
    create_award_base_event, create_block_event, get_laserball_game_id, create_zap_event, create_missile_event, \
    create_team


class TestStatsHelper(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await setup_test_database()

    async def asyncTearDown(self):
        await teardown_test_database()

    async def test_count_zaps(self):
        game = await SM5Game.filter(id=get_sm5_game_id()).first()
        zaps = await count_zaps(game, ENTITY_ID_1, ENTITY_ID_2)
        self.assertEqual(3, zaps)

    async def test_count_blocks(self):
        game = await LaserballGame.filter(id=get_laserball_game_id()).first()

        await game.events.add(
            await create_block_event(time_millis=1000, blocking_entity_id=ENTITY_ID_1, blocked_entity_id=ENTITY_ID_2))
        await game.events.add(
            await create_block_event(time_millis=50000, blocking_entity_id=ENTITY_ID_1, blocked_entity_id=ENTITY_ID_2))
        await game.events.add(
            await create_block_event(time_millis=80000, blocking_entity_id=ENTITY_ID_2, blocked_entity_id=ENTITY_ID_1))
        await game.events.add(
            await create_block_event(time_millis=90000, blocking_entity_id=ENTITY_ID_1, blocked_entity_id=ENTITY_ID_3))
        await game.events.add(
            await create_zap_event(time_millis=95000, zapping_entity_id=ENTITY_ID_1, zapped_entity_id=ENTITY_ID_2))
        await game.events.add(
            await create_missile_event(time_millis=98000, missiling_entity_id=ENTITY_ID_1,
                                       missiled_entity_id=ENTITY_ID_2))

        zaps = await count_blocks(game, ENTITY_ID_1, ENTITY_ID_2)
        self.assertEqual(2, zaps)

    async def test_count_missiles(self):
        game = await SM5Game.filter(id=get_sm5_game_id()).first()

        await game.events.add(
            await create_missile_event(time_millis=1000, missiling_entity_id=ENTITY_ID_1,
                                       missiled_entity_id=ENTITY_ID_2))
        await game.events.add(
            await create_missile_event(time_millis=50000, missiling_entity_id=ENTITY_ID_1,
                                       missiled_entity_id=ENTITY_ID_2))
        await game.events.add(
            await create_missile_event(time_millis=80000, missiling_entity_id=ENTITY_ID_2,
                                       missiled_entity_id=ENTITY_ID_1))
        await game.events.add(
            await create_missile_event(time_millis=90000, missiling_entity_id=ENTITY_ID_1,
                                       missiled_entity_id=ENTITY_ID_3))
        await game.events.add(
            await create_block_event(time_millis=92000, blocking_entity_id=ENTITY_ID_1, blocked_entity_id=ENTITY_ID_2))
        await game.events.add(
            await create_zap_event(time_millis=95000, zapping_entity_id=ENTITY_ID_1, zapped_entity_id=ENTITY_ID_2))

        zaps = await count_missiles(game, ENTITY_ID_1, ENTITY_ID_2)
        self.assertEqual(2, zaps)

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

    async def test_get_points_scored(self):
        game = await SM5Game.filter(id=get_sm5_game_id()).first()

        entity1, entity_end1 = await add_entity(entity_id=ENTITY_ID_1, team=get_red_team(), score=3000)
        entity2, entity_end2 = await add_entity(entity_id=ENTITY_ID_2, team=get_red_team(), score=50000)
        entity3, entity_end3 = await add_entity(entity_id=ENTITY_ID_3, team=get_green_team(), score=700000)

        await game.entity_ends.add(*[entity_end1, entity_end2, entity_end3])

        game2 = await SM5Game.create(winner_color=Team.RED.value.color, tdf_name="in_memory_test",
                                     file_version="0.test.0",
                                     software_version="12.34.56", arena="Test Arena", mission_name="Space Marines 5",
                                     mission_type=0, ranked=True, ended_early=False, start_time=2222222,
                                     mission_duration=900000)

        red_team_2 = await create_team(0, Team.RED)
        green_team_2 = await create_team(1, Team.GREEN)

        entity1, entity_end1 = await add_entity(entity_id=ENTITY_ID_1, team=get_red_team(), score=3)
        entity2, entity_end2 = await add_entity(entity_id=ENTITY_ID_2, team=get_red_team(), score=50)
        entity3, entity_end3 = await add_entity(entity_id=ENTITY_ID_3, team=get_green_team(), score=700)

        await game2.teams.add(*[red_team_2, green_team_2])
        await game2.entity_ends.add(*[entity_end1, entity_end2, entity_end3])

        total_points_scored = await get_points_scored()

        self.assertEqual(753753, total_points_scored)

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
