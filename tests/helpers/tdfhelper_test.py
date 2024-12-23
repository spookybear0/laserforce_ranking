import datetime
import os
import unittest

from pytz import utc

from db.types import Team
from helpers.tdfhelper import parse_sm5_game
from tests.helpers.environment import setup_test_database, teardown_test_database


class TestTdfHelper(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await setup_test_database()

    async def asyncTearDown(self):
        await teardown_test_database()

    async def testImportSm5(self):
        game = await parse_sm5_game(self._get_test_data_path("sm5_game1.tdf"))

        self.assertEqual(Team.RED, game.winner)
        self.assertEqual(Team.RED.value.color, game.winner_color)
        self.assertEqual("Space Marines 5 Tournament Edition", game.mission_name)
        self.assertEqual(True, game.ranked)
        self.assertEqual(False, game.ended_early)
        self.assertEqual(datetime.datetime(year=2024, month=1, day=14, hour=20, minute=57, second=10, tzinfo=utc),
                         game.start_time)
        self.assertEqual(900000, game.mission_duration)

        teams = [await team.to_dict() for team in await game.teams.all()]
        self.assertEqual([
            {
                "index": 0,
                "name": "Fire Team",
                "color_enum": 11,
                "color_name": "Fire",
                "real_color_name": "Red",
            },
            {
                "index": 1,
                "name": "Earth Team",
                "color_enum": 13,
                "color_name": "Earth",
                "real_color_name": "Green",
            },
            {
                "index": 2,
                "name": "Neutral",
                "color_enum": 0,
                "color_name": "None",
                "real_color_name": "None",
            },
        ], teams)

    @staticmethod
    def _get_test_data_path(filename: str) -> str:
        """Returns the full path of a file within the tests/data folder."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", filename)


if __name__ == '__main__':
    unittest.main()
