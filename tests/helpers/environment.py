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

from db.game import Events, EntityStarts, Teams, EntityEnds
from db.sm5 import SM5Game
from db.types import EventType, Team
from helpers.tdfhelper import create_event_from_data

ENTITY_ID_1 = "Entity#1"
ENTITY_ID_2 = "Entity#2"
ENTITY_ID_3 = "Entity#3"
ENTITY_ID_4 = "Entity#4"

_RED_TEAM: Optional[Teams] = None
_BLUE_TEAM: Optional[Teams] = None
_GREEN_TEAM: Optional[Teams] = None

_TEST_SM5_GAME: Optional[SM5Game] = None


def get_sm5_game_id() -> int:
    """Returns the game ID of the test SM5 game.

    May only be called after the database has been initialized with setup_test_database()."""
    assert _TEST_SM5_GAME
    return _TEST_SM5_GAME.id


def get_red_team() -> Teams:
    assert _RED_TEAM
    return _RED_TEAM


def get_green_team() -> Teams:
    assert _GREEN_TEAM
    return _GREEN_TEAM


async def setup_test_database():
    """Creates a test in-memory database using SQLite, connects Tortoise to it, and generates the schema.

    It will also generate the test dataset."""
    global _TEST_SM5_GAME, _RED_TEAM, _GREEN_TEAM, _BLUE_TEAM

    await Tortoise.init(db_url="sqlite://:memory:",
                        modules={
                            "models": ["db.game", "db.laserball", "db.legacy", "db.player", "db.sm5", "aerich.models"]})

    await Tortoise.generate_schemas()

    _RED_TEAM = await Teams.create(index=0, name="Fire Team", color_enum=0, color_name=Team.RED.element,
                                   real_color_name=Team.RED.standardize())
    _GREEN_TEAM = await Teams.create(index=1, name="Earth Team", color_enum=1, color_name=Team.GREEN.element,
                                     real_color_name=Team.GREEN.standardize())
    _BLUE_TEAM = await Teams.create(index=2, name="Ice Team", color_enum=2, color_name=Team.BLUE.element,
                                    real_color_name=Team.BLUE.standardize())

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


async def add_sm5_event(event: Events):
    assert _TEST_SM5_GAME

    await _TEST_SM5_GAME.events.add(event)


async def create_zap_event(time_millis: int, zapping_entity_id: str, zapped_entity_id: str) -> Events:
    return await create_event_from_data(
        ["4", str(time_millis), EventType.DOWNED_OPPONENT, zapping_entity_id, " zaps ", zapped_entity_id])


async def create_destroy_base_event(time_millis: int, destroying_entity_id: str, base_entity_str: str) -> Events:
    return await create_event_from_data(
        ["4", str(time_millis), EventType.DESTROY_BASE, destroying_entity_id, " destroys ", base_entity_str])


async def create_mission_end_event(time_millis) -> Events:
    return await create_event_from_data(["4", str(time_millis), EventType.MISSION_END, "* Mission End *"])


async def add_entity(
        entity_id: str,
        team: Teams,
        start_time_millis: int = 0,
        end_time_millis: int = 900000,
        type: str = "player",
        name: str = "Some Player",
        level: int = 0,
        role: int = 0,
        battlesuit: str = "Panther",
        member_id: str = "4-43-000",
        score: int = 0,
        sm5_game: Optional[SM5Game] = None
) -> (EntityStarts, EntityEnds):
    entity_start = await create_entity_start(
        entity_id=entity_id,
        team=team,
        time_millis=start_time_millis,
        type=type,
        name=name,
        level=level,
        role=role,
        battlesuit=battlesuit,
        member_id=member_id
    )

    entity_end = await create_entity_ends(
        entity_start=entity_start,
        time_millis=end_time_millis,
        score=score
    )

    if sm5_game:
        await sm5_game.entity_starts.add(entity_start)
        await sm5_game.entity_ends.add(entity_end)

    return entity_start, entity_end


async def create_entity_start(
        entity_id: str,
        team: Teams,
        time_millis: int = 0,
        type: str = "player",
        name: str = "Some Player",
        level: int = 0,
        role: int = 0,
        battlesuit: str = "Panther",
        member_id: str = "4-43-000"
) -> EntityStarts:
    return await EntityStarts.create(time=time_millis,
                                     entity_id=entity_id,
                                     type=type,
                                     name=name,
                                     team=team,
                                     level=level,
                                     role=role,
                                     battlesuit=battlesuit,
                                     member_id=member_id)


async def create_entity_ends(
        entity_start: EntityStarts,
        time_millis: int = 90000,
        type: int = 1,
        score: int = 0) -> EntityEnds:
    return await EntityEnds.create(time=time_millis,
                                   entity=entity_start,
                                   type=type,
                                   score=score)
