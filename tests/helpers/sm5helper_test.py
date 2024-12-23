import unittest

from db.sm5 import SM5Game
from db.types import Team
from helpers.sm5helper import get_sm5_last_team_standing
from tests.helpers.environment import setup_test_database, ENTITY_ID_1, ENTITY_ID_2, get_sm5_game_id, \
    teardown_test_database, add_entity, get_red_team, get_green_team, add_sm5_stats


class TestSm5Helper(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await setup_test_database()

    async def asyncTearDown(self):
        await teardown_test_database()

    async def test_get_sm5_last_team_standing_both_alive(self):
        game = await SM5Game.filter(id=get_sm5_game_id()).first()
        entity_start, entity_end = await add_entity(entity_id=ENTITY_ID_1, team=get_red_team())
        stats = await add_sm5_stats(entity_start, lives_left=10)

        entity_start2, entity_end2 = await add_entity(entity_id=ENTITY_ID_2, team=get_green_team())
        stats2 = await add_sm5_stats(entity_start2, lives_left=15)

        await game.entity_starts.add(entity_start, entity_start2)
        game = await SM5Game.filter(id=get_sm5_game_id()).first()

        winning_team = await get_sm5_last_team_standing(game)

        self.assertEqual(None, winning_team)

    async def test_get_sm5_last_team_standing_only_red_alive(self):
        game = await SM5Game.filter(id=get_sm5_game_id()).first()
        entity_start, entity_end = await add_entity(entity_id=ENTITY_ID_1, team=get_red_team())
        await add_sm5_stats(entity_start, lives_left=10)

        entity_start2, entity_end2 = await add_entity(entity_id=ENTITY_ID_2, team=get_green_team())
        await add_sm5_stats(entity_start2, lives_left=0)

        await game.entity_starts.add(entity_start, entity_start2)
        game = await SM5Game.filter(id=get_sm5_game_id()).first()

        winning_team = await get_sm5_last_team_standing(game)

        self.assertEqual(Team.RED, winning_team)


if __name__ == '__main__':
    unittest.main()
