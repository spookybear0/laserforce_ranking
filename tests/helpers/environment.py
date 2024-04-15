"""Basic test environment for all laserforce_ranking tests.

Sets up a Tortoise environment with an in-memory SQLite database, creates some basic test games, exposes their IDs, and
has functions to create specific scenarios for whatever is needed for a unit test.

For some unit tests, it's better to create minimal setups that just have the bare minimum necessary for the system under
test. But there are function where every part of the game matters, so we'll have this complete game here as a test
dataset.
"""
import json
import os
from typing import Optional

from tortoise import Tortoise

from db.game import Events, EntityStarts, Teams, EntityEnds, Scores
from db.laserball import LaserballGame
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
_TEST_LASERBALL_GAME: Optional[LaserballGame] = None


def get_sm5_game_id() -> int:
    """Returns the game ID of the test SM5 game.

    May only be called after the database has been initialized with setup_test_database()."""
    assert _TEST_SM5_GAME
    return _TEST_SM5_GAME.id


def get_laserball_game_id() -> int:
    """Returns the game ID of the test Laserball game.

    May only be called after the database has been initialized with setup_test_database()."""
    assert _TEST_LASERBALL_GAME
    return _TEST_LASERBALL_GAME.id


def get_red_team() -> Teams:
    assert _RED_TEAM
    return _RED_TEAM


def get_green_team() -> Teams:
    assert _GREEN_TEAM
    return _GREEN_TEAM


def get_blue_team() -> Teams:
    assert _BLUE_TEAM
    return _BLUE_TEAM


async def setup_test_database(basic_events: bool = True):
    """Creates a test in-memory database using SQLite, connects Tortoise to it, and generates the schema.

    It will also generate the test dataset."""
    global _TEST_SM5_GAME, _TEST_LASERBALL_GAME, _RED_TEAM, _GREEN_TEAM, _BLUE_TEAM

    await Tortoise.init(db_url="sqlite://:memory:",
                        modules={
                            "models": ["db.game", "db.laserball", "db.legacy", "db.player", "db.sm5", "aerich.models"]})

    await Tortoise.generate_schemas()

    _RED_TEAM = await create_team(0, Team.RED)
    _GREEN_TEAM = await create_team(1, Team.GREEN)
    _BLUE_TEAM = await create_team(2, Team.BLUE)

    _TEST_SM5_GAME = await create_sm5_game_1(basic_events=basic_events)
    _TEST_LASERBALL_GAME = await create_laserball_game_1()


async def teardown_test_database():
    await Tortoise.close_connections()


async def create_sm5_game_1(basic_events: bool = True) -> SM5Game:
    events = []

    if basic_events:
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

    await game.teams.add(*[_RED_TEAM, _GREEN_TEAM])
    await game.events.add(*events)
    await game.save()
    return game


async def create_laserball_game_1() -> LaserballGame:
    game = await LaserballGame.create(winner=Team.RED, winner_color=Team.RED.value.color, tdf_name="in_memory_test",
                                      file_version="0.test.0",
                                      software_version="12.34.56", arena="Test Arena", mission_name="Laserball",
                                      mission_type=0, ranked=True, ended_early=False, start_time=2222222,
                                      mission_duration=900000)

    await game.save()
    return game


async def add_sm5_event(event: Events):
    assert _TEST_SM5_GAME

    await _TEST_SM5_GAME.events.add(event)


async def create_zap_event(time_millis: int, zapping_entity_id: str, zapped_entity_id: str) -> Events:
    return await create_event_from_data(
        ["4", str(time_millis), EventType.DOWNED_OPPONENT, zapping_entity_id, " zaps ", zapped_entity_id])


async def create_block_event(time_millis: int, blocking_entity_id: str, blocked_entity_id: str) -> Events:
    return await create_event_from_data(
        ["4", str(time_millis), EventType.BLOCK, blocking_entity_id, " blocks ", blocked_entity_id])


async def create_missile_event(time_millis: int, missiling_entity_id: str, missiled_entity_id: str) -> Events:
    return await create_event_from_data(
        ["4", str(time_millis), EventType.MISSILE_DOWN_OPPONENT, missiling_entity_id, " missiles ", missiled_entity_id])


async def create_destroy_base_event(time_millis: int, destroying_entity_id: str, base_entity_str: str) -> Events:
    return await create_event_from_data(
        ["4", str(time_millis), EventType.DESTROY_BASE, destroying_entity_id, " destroys ", base_entity_str])


async def create_award_base_event(time_millis: int, destroying_entity_id: str, base_entity_str: str) -> Events:
    return await create_event_from_data(
        ["4", str(time_millis), EventType.BASE_AWARDED, destroying_entity_id, " is awarded ", base_entity_str])


async def create_mission_end_event(time_millis) -> Events:
    return await create_event_from_data(["4", str(time_millis), EventType.MISSION_END, "* Mission End *"])


async def create_resupply_lives_event(time_millis: int, supplier_entity_id: str, supplyee_entity_id: str) -> Events:
    return await create_event_from_data(
        ["4", str(time_millis), EventType.RESUPPLY_LIVES, supplier_entity_id, " resupplies ", supplyee_entity_id])


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
        sm5_game: Optional[SM5Game] = None,
        omit_entity_end: bool = False,
) -> (EntityStarts, Optional[EntityEnds]):
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

    if sm5_game:
        await sm5_game.entity_starts.add(entity_start)

    if omit_entity_end:
        entity_end = None
    else:
        entity_end = await create_entity_ends(
            entity_start=entity_start,
            time_millis=end_time_millis,
            score=score
        )
        if sm5_game:
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


async def create_team(index: int, team: Team) -> Teams:
    return await Teams.create(index=index, name=f"{team.element} Team", color_enum=index, color_name=team.element,
                              real_color_name=team.standardize())


async def add_sm5_score(game: SM5Game, entity: EntityStarts, time_millis: int, old_score: int, score: int):
    score = await Scores.create(entity=entity, time=time_millis, old=old_score, delta=score - old_score, new=score)

    await game.scores.add(score)


def get_test_data_path(filename: str) -> str:
    """Returns the full path of a file within the tests/data folder."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", filename)
