import unittest

from db.sm5 import SM5Game
from helpers.statshelper import count_zaps
from tests.helpers.environment import setup_test_database, ENTITY_ID_1, ENTITY_ID_2, get_sm5_game_id, teardown_test_database


class TestStatsHelper(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await setup_test_database()

    async def asyncTearDown(self):
        await teardown_test_database()

    async def test_count_zaps(self):
        game = await SM5Game.filter(id=get_sm5_game_id()).first()
        zaps = await count_zaps(game, ENTITY_ID_1, ENTITY_ID_2)
        self.assertEqual(3, zaps)


if __name__ == '__main__':
    unittest.main()
