import unittest

from db.sm5 import SM5Game
from db.types import Team
from tests.helpers.environment import setup_test_database, get_sm5_game_id, add_sm5_event, \
    create_mission_end_event, add_entity, get_red_team, get_green_team, ENTITY_ID_1, ENTITY_ID_2, ENTITY_ID_3, \
    ENTITY_ID_4


class TestSm5(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await setup_test_database()

    async def test_get_actual_game_duration_full_length(self):
        game = await SM5Game.filter(id=get_sm5_game_id()).first()

        # The default duration for an SM5 game is 15 minutes (900,000ms).
        self.assertEqual(900000, await game.get_actual_game_duration())

    async def test_get_actual_game_duration_early_termination(self):
        await add_sm5_event(await create_mission_end_event(88888))

        game = await SM5Game.filter(id=get_sm5_game_id()).first()

        self.assertEqual(88888, await game.get_actual_game_duration())

    async def test_get_team_score(self):
        game = await SM5Game.filter(id=get_sm5_game_id()).first()

        # Shouldn't count, this entity isn't part of this game.
        await add_entity(entity_id=ENTITY_ID_1, score=4000, team=get_red_team())
        # Should count.
        await add_entity(entity_id=ENTITY_ID_2, score=300, team=get_red_team(), sm5_game=game)
        # Should count.
        await add_entity(entity_id=ENTITY_ID_3, score=20, team=get_red_team(), sm5_game=game)
        # Shouldn't count, this entity is on a different team.
        await add_entity(entity_id=ENTITY_ID_4, score=1, team=get_green_team(), sm5_game=game)

        self.assertEqual(320, await game.get_team_score(Team.RED))


if __name__ == '__main__':
    unittest.main()
