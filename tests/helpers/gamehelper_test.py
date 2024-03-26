import unittest

from db.sm5 import SM5Game, SM5Stats
from helpers.gamehelper import get_players_from_team
from helpers.statshelper import count_zaps, get_sm5_kd_ratio, get_sm5_score_components
from tests.helpers.environment import setup_test_database, ENTITY_ID_1, ENTITY_ID_2, get_sm5_game_id, \
    teardown_test_database, create_destroy_base_event, add_entity, get_red_team


class TestGameHelper(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await setup_test_database()

    async def asyncTearDown(self):
        await teardown_test_database()

    async def test_get_players_from_team(self):
        player1 = {
            "name": "Indy",
            "team": 0,
        }
        player2 = {
            "name": "Barbie",
            "team": 1,
        }
        player3 = {
            "name": "Sonic",
            "team": 1,
        }

        players_in_team = get_players_from_team([player1, player2, player3], team_index=1)

        self.assertCountEqual([player2, player3], players_in_team)


if __name__ == '__main__':
    unittest.main()
