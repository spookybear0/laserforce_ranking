"""Basic test environment for all laserforce_ranking tests.

Sets up a Tortoise environment with an in-memory SQLite database, creates some basic test games, exposes their IDs, and
has functions to create specific scenarios for whatever is needed for a unit test.

For some unit tests, it's better to create minimal setups that just have the bare minimum necessary for the system under
test. But there are function where every part of the game matters, so we'll have this complete game here as a test
dataset.
"""
import json
from typing import Optional

from tortoise import Tortoise

from db.game import Events
from db.sm5 import SM5Game
from db.types import EventType, Team
from helpers.tdfhelper import create_event_from_data

ENTITY_ID_1 = "Entity#1"
ENTITY_ID_2 = "Entity#2"
ENTITY_ID_3 = "Entity#3"

_TEST_SM5_GAME: Optional[SM5Game] = None


def get_sm5_game_id() -> int:
    """Returns the game ID of the test SM5 game.

    May only be called after the database has been initialized with setup_test_database()."""
    assert _TEST_SM5_GAME
    return _TEST_SM5_GAME.id


async def setup_test_database():
    """Creates a test in-memory database using SQLite, connects Tortoise to it, and generates the schema.

    It will also generate the test dataset."""
    global _TEST_SM5_GAME

    await Tortoise.init(db_url="sqlite://:memory:",
                        modules={
                            "models": ["db.game", "db.laserball", "db.legacy", "db.player", "db.sm5", "aerich.models"]})

    await Tortoise.generate_schemas()

    _TEST_SM5_GAME = await create_sm5_game_1()


async def teardown_test_database():
    await Tortoise.close_connections()


async def create_sm5_game_1() -> SM5Game:
    events = []
    events.extend([await create_zap_event(100, ENTITY_ID_1, ENTITY_ID_2),
                   await create_zap_event(200, ENTITY_ID_1, ENTITY_ID_2),
                   await create_zap_event(400, ENTITY_ID_2, ENTITY_ID_1),
                   await create_zap_event(500, ENTITY_ID_1, ENTITY_ID_2),
                   await Events.create(time=600, type=EventType.ACTIVATE_NUKE,
                                       arguments=json.dumps([ENTITY_ID_2, " nukes ", ENTITY_ID_1])),
                   await create_zap_event(700, ENTITY_ID_3, ENTITY_ID_1),
                   await create_zap_event(800, ENTITY_ID_1, ENTITY_ID_3),
                   ])

    game = await SM5Game.create(winner_color=Team.RED.value.color, tdf_name="in_memory_test", file_version="0.test.0",
                                software_version="12.34.56", arena="Test Arena", mission_name="Space Marines 5",
                                mission_type=0, ranked=True, ended_early=False, start_time=2222222,
                                mission_duration=900000)

    await game.events.add(*events)
    await game.save()
    return game


async def create_zap_event(time_millis: int, zapping_entity_id: str, zapped_entity_id: str) -> Events:
    return await create_event_from_data(
        ["4", str(time_millis), EventType.DOWNED_OPPONENT, zapping_entity_id, " zaps ", zapped_entity_id])
