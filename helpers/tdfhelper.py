import json
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional

import sentry_sdk
from sanic.log import logger
from sanic import Request

from db.game import EntityEnds, EntityStarts, Events, Scores, PlayerStates, Teams
from db.laserball import LaserballGame, LaserballStats
from db.player import Player
from db.sm5 import IntRole, SM5_LASERRANK_VERSION
from db.sm5 import SM5Game, SM5Stats
from db.types import EventType, PlayerStateType, Team, Permission
from helpers import ratinghelper
from helpers import sm5helper, laserballhelper
from helpers.ratinghelper import MU, SIGMA
from helpers.cachehelper import _precache_template


def element_to_color(element: str) -> str:
    conversion = {
        "Fire": "Red",
        "Ice": "Blue",
        "Earth": "Green",
        "None": "None",

        # extras for edge cases
        "Green": "Green",
        "Red": "Red",
        "Blue": "Blue",
        "Yellow": "Yellow",
        "Purple": "Purple",
        "Solid Green": "Green",
        "Solid Red": "Red",
        "Solid Blue": "Blue",
        "Solid Yellow": "Yellow",
        "Solid Purple": "Purple",
    }

    return conversion[element]

async def precache_game(type: str, id: int) -> None:
    if "pytest" in sys.modules:
        # don't precache when running tests
        return

    from shared import app

    logger.debug(f"Precaching game {type} {id}")
    request = Request(bytes(f"/game/{type}/{id}", encoding="utf-8"), {}, "", "GET", None, app)

    request.ctx.session = {
        "permissions": Permission.USER
    }

    await app.router.find_route_by_view_name("game_index").handler(request, type=type, id=id)
    logger.debug(f"Precached game {type} {id}")


async def parse_sm5_game(file_location: str) -> Optional[SM5Game]:
    file = open(file_location, "r", encoding="utf-16")
    logger.info(f"Parsing {file_location}...")

    file_version = ""
    program_version = ""
    arena = ""

    mission_type = 0
    mission_name = ""
    start_time: str = ""
    mission_duration = 0

    teams: List[Teams] = []
    entity_starts: List[EntityStarts] = []
    events: List[Events] = []
    scores: List[Scores] = []
    entity_ends: List[EntityEnds] = []
    sm5_stats: List[SM5Stats] = []
    player_states: List[PlayerStates] = []

    token_to_entity = {}

    # default values, will be changed later

    ranked = True
    ended_early = True  # will be changed to false if there's a mission end event

    linenum = 0
    while True:
        linenum += 1
        line = file.readline()
        if not line:
            break

        data = line.rstrip("\n").split("\t")
        match data[0]:  # switch on the first element of the line
            case ";":
                continue  # comment
            case "0":  # system info
                sentry_sdk.set_context("system_info",
                                       {"file_version": data[1], "program_version": data[2], "arena": data[3]})

                file_version = data[1]
                program_version = data[2]
                arena = data[3]
                logger.debug(
                    f"System Info: file version: {file_version}, program version: {program_version}, arena: {arena}")
            case "1":  # game info
                sentry_sdk.set_context("game_info",
                                       {"mission_type": data[1], "mission_name": data[2], "start_time": data[3],
                                        "mission_duration": data[4]})

                mission_type = int(data[1])
                mission_name = data[2]
                start_time = data[3]
                mission_duration = int(data[4])

                logger.debug(
                    f"Game Info: mission type: {mission_type}, mission name: {mission_name}, start time: {start_time}, mission duration: {mission_duration}")

                # check if game already exists
                if game := await SM5Game.filter(start_time=start_time, arena=arena).first():

                    # triple check it because since the timestamp gets rounded, it's possible for
                    # games to start at nearly the same time

                    if file_location == "sm5_tdf/" + game.tdf_name:
                        logger.warning(f"Game {game.id} already exists, skipping")
                        return game
                    
                if mission_type != 5:
                    # only parse sm5 games (mission type 5)

                    logger.warning(f"Game at {file_location} is not an SM5 game (mission type {mission_type}), skipping")
                    return None

            case "2":  # team info
                sentry_sdk.set_context("team_info", {"index": data[1], "name": data[2], "color_enum": data[3],
                                                     "color_name": data[4]})

                teams.append(
                    await Teams.create(index=int(data[1]), name=data[2], color_enum=data[3], color_name=data[4],
                                       real_color_name=element_to_color(data[4])))
                logger.debug(
                    f"Team Info: index: {data[1]}, name: {data[2]}, color enum: {data[3]}, color name: {data[4]}")
            case "3":  # entity start
                team = None

                # what team is this player on?
                # iterate through teams until we find the right one and save it to "team"
                for t in teams:
                    if t.index == int(data[5]):
                        team = t
                        break

                if team is None:
                    raise Exception("Team not found, invalid tdf file")

                # has index 9
                try:
                    member_id = data[9]
                except (ValueError, IndexError):
                    member_id = None

                sentry_sdk.set_context(
                    "entity_start", {
                        "time": data[1],
                        "entity_id": data[2],
                        "type": data[3],
                        "name": data[4],
                        "team": data[5],
                        "level": data[6],
                        "role": data[7],
                        "battlesuit": data[8],
                        "member_id": member_id
                    }
                )

                name = data[4].strip()  # remove whitespace (some names have trailing whitespace for some reason)

                entity_start = await EntityStarts.create(time=int(data[1]), entity_id=data[2], type=data[3], name=name,
                                                         team=team, level=int(data[6]), role=int(data[7]),
                                                         battlesuit=data[8], member_id=member_id)

                entity_starts.append(entity_start)
                token_to_entity[data[2]] = entity_start
            case "4":  # event
                sentry_sdk.set_context("event", {"time": data[1], "type": data[2], "arguments": data[3:]})
                
                events.append(await create_event_from_data(data))

                if EventType(data[2]) == EventType.MISSION_END:  # game ended naturally
                    ended_early = False

                logger.debug(f"Event: time: {data[1]}, type: {EventType(data[2])}, arguments: {data[3:]}")
            case "5":  # score
                sentry_sdk.set_context("score", {"time": data[1], "entity": data[2], "old": data[3], "delta": data[4],
                                                 "new": data[5]})

                scores.append(await Scores.create(time=int(data[1]), entity=token_to_entity[data[2]], old=int(data[3]),
                                                  delta=int(data[4]), new=int(data[5])))
                logger.debug(
                    f"Score: time: {data[1]}, entity: {token_to_entity[data[2]]}, old: {data[3]}, delta: {data[4]}, new: {data[5]}")
            case "6":  # entity end
                sentry_sdk.set_context("entity_end",
                                       {"time": data[1], "entity": data[2], "type": data[3], "score": data[4]})

                entity_ends.append(await EntityEnds.create(time=int(data[1]), entity=token_to_entity[data[2]],
                                                           type=int(data[3]), score=int(data[4])))
                logger.debug(
                    f"Entity End: time: {data[1]}, entity: {token_to_entity[data[2]]}, type: {data[3]}, score: {data[4]}")
            case "7":  # sm5 stats
                sentry_sdk.set_context(
                    "sm5_stats", {
                        "entity": data[1],
                        "shots_hit": data[2],
                        "shots_fired": data[3],
                        "times_zapped": data[4],
                        "times_missiled": data[5],
                        "missile_hits": data[6],
                        "nukes_detonated": data[7],
                        "nukes_activated": data[8],
                        "nuke_cancels": data[9],
                        "medic_hits": data[10],
                        "own_medic_hits": data[11],
                        "medic_nukes": data[12],
                        "scout_rapid_fires": data[13],
                        "life_boosts": data[14],
                        "ammo_boosts": data[15],
                        "lives_left": data[16],
                        "shots_left": data[17],
                        "penalties": data[18],
                        "shot_3_hits": data[19],
                        "own_nuke_cancels": data[20],
                        "shot_opponent": data[21],
                        "shot_team": data[22],
                        "missiled_opponent": data[23],
                        "missiled_team": data[24]
                    }
                )

                sm5_stats.append(await SM5Stats.create(entity=token_to_entity[data[1]],
                                                       shots_hit=int(data[2]), shots_fired=int(data[3]),
                                                       times_zapped=int(data[4]), times_missiled=int(data[5]),
                                                       missile_hits=int(data[6]), nukes_detonated=int(data[7]),
                                                       nukes_activated=int(data[8]), nuke_cancels=int(data[9]),
                                                       medic_hits=int(data[10]), own_medic_hits=int(data[11]),
                                                       medic_nukes=int(data[12]), scout_rapid_fires=int(data[13]),
                                                       life_boosts=int(data[14]), ammo_boosts=int(data[15]),
                                                       lives_left=int(data[16]), shots_left=int(data[17]),
                                                       penalties=int(data[18]), shot_3_hits=int(data[19]),
                                                       own_nuke_cancels=int(data[20]), shot_opponent=int(data[21]),
                                                       shot_team=int(data[22]), missiled_opponent=int(data[23]),
                                                       missiled_team=int(data[24])))

                logger.debug(
                    f"SM5 Stats: entity: {token_to_entity[data[1]]}, shots hit: {data[2]}, shots fired: {data[3]}, times zapped: {data[4]}, times missiled: {data[5]}, missile hits: {data[6]}, nukes detonated: {data[7]}, nukes activated: {data[8]}, nuke cancels: {data[9]}, medic hits: {data[10]}, own medic hits: {data[11]}, medic nukes: {data[12]}, scout rapid fires: {data[13]}, life boosts: {data[14]}, ammo boosts: {data[15]}, lives left: {data[16]}, shots left: {data[17]}, penalties: {data[18]}, shot 3 hits: {data[19]}, own nuke cancels: {data[20]}, shot opponent: {data[21]}, shot team: {data[22]}, missiled opponent: {data[23]}, missiled team: {data[24]}")
            case "9":  # player state
                sentry_sdk.set_context("player_state", {"time": data[1], "entity": data[2], "state": data[3]})

                player_states.append(await PlayerStates.create(time=int(data[1]), entity=token_to_entity[data[2]],
                                                               state=PlayerStateType(int(data[3]))))
                logger.debug(
                    f"Player State: time: {int(data[1])}, entity: {token_to_entity[data[2]]}, state: {data[3]}")

    # get teams for later use

    team1 = None
    team2 = None

    index = 1

    for t in teams:
        if not t.color_name or not t.color_enum or t.name == "Neutral":
            continue

        if index == 1:
            team1 = t
        else:  # 2
            team2 = t

        index += 1

    # before creating the game, we need to make sure this game wasn't a false start
    # which means that game ended early and it lasted less than 3 minutes

    if ended_early and mission_duration < 3 * 60 * 1000:
        logger.warning("Game ended early and lasted less than 3 minutes, skipping")
        return None

    game = await SM5Game.create(winner=Team.NONE, winner_color="none", tdf_name=os.path.basename(file_location),
                                file_version=file_version, ranked=ranked,
                                software_version=program_version, arena=arena, mission_type=mission_type,
                                mission_name=mission_name,
                                start_time=datetime.strptime(start_time, "%Y%m%d%H%M%S"),
                                mission_duration=mission_duration, ended_early=ended_early)

    sentry_sdk.set_context("game", {"id": game.id})

    await game.teams.add(*teams)
    await game.entity_starts.add(*entity_starts)
    await game.events.add(*events)
    await game.player_states.add(*player_states)
    await game.scores.add(*scores)
    await game.entity_ends.add(*entity_ends)
    await game.sm5_stats.add(*sm5_stats)

    await game.save()

    logger.debug("Inital game save complete")
    await sm5helper.update_winner(game)

    game.laserrank_version = SM5_LASERRANK_VERSION
    await game.save()

    logger.debug(f"Winner: {game.winner_color}")

    # determine if the game should be ranked automatically

    # 5 < team size < 7 and teams are not of unequal size (ratings are not tested for unequal team sizes)

    team1_len = await game.entity_ends.filter(entity__team=team1, entity__type="player").count()
    team2_len = await game.entity_ends.filter(entity__team=team2, entity__type="player").count()

    if team1_len > 7 or team2_len > 7 or team1_len < 5 or team2_len < 5 or team1_len != team2_len:
        ranked = False

    # also check that our roles are correct
    # ex: a standard sm5 team has 1 commander, 1 heavy, 1 scout, 1 medic, 1 ammo, and 1-3 scouts

    # for each team
    for t in teams:
        total_count = 0
        commander_count = 0
        heavy_count = 0
        scout_count = 0
        ammo_count = 0
        medic_count = 0

        for e in entity_starts:
            if e.type == "player" and e.team == t:
                total_count += 1
                if e.role == IntRole.COMMANDER:
                    commander_count += 1
                elif e.role == IntRole.HEAVY:
                    heavy_count += 1
                elif e.role == IntRole.SCOUT:
                    scout_count += 1
                elif e.role == IntRole.AMMO:  # sometimes we have 2 ammos, but for ranking purposes we only want games with 1
                    ammo_count += 1
                elif e.role == IntRole.MEDIC:
                    medic_count += 1

        if total_count == 0:  # probably a neutral team
            continue

        if commander_count != 1 or heavy_count != 1 or ammo_count != 1 or medic_count != 1 or scout_count < 1 or scout_count > 3:
            ranked = False

    # check if there are any non-member players

    for e in entity_starts:
        if e.type == "player" and e.entity_id.startswith("@") and e.name == e.battlesuit:
            ranked = False
            break

    # check if game was ended early (but not by elimination)

    # ended_early = if there's a mission end event (natural end by time or elim)
    # value set in event parsing

    sentry_sdk.set_context("game_info", {"ranked": ranked, "ended_early": ended_early})

    logger.debug(f"Ranked={ranked}, Ended Early={ended_early}")

    game.ranked = ranked
    game.ended_early = ended_early
    game.team1_size = team1_len
    game.team2_size = team2_len

    await game.save()

    logger.info("Resyncing player table")

    # add new players to the database

    for e in entity_starts:
        # is a player and logged in
        if e.entity_id.startswith("@") and e.name == e.battlesuit:
            continue

        db_member_id = e.member_id if e.member_id else ""

        if e.type == "player":
            # update entity_id if it's empty
            if await Player.filter(codename=e.name).exists() and (
                    await Player.filter(codename=e.name).first()).entity_id == "":
                player = await Player.filter(codename=e.name).first()
                player.entity_id = e.entity_id
                player.player_id = db_member_id
                await player.save()
            # update player name if we have a new one and we have entity_id
            elif await Player.filter(entity_id=e.entity_id).exists() and (
                    await Player.filter(entity_id=e.entity_id).first()).codename != e.name:
                player = await Player.filter(entity_id=e.entity_id).first()
                player.codename = e.name
                player.player_id = db_member_id
                await player.save()
            # update player_id if we have entity_id and don't have player_id
            elif await Player.filter(entity_id=e.entity_id).exists() and (
                    await Player.filter(entity_id=e.entity_id).first()).player_id == "":
                player = await Player.filter(entity_id=e.entity_id).first()
                player.player_id = db_member_id
                await player.save()
            # create new player if we don't have a name or entity_id
            elif not await Player.filter(codename=e.name).exists() and not await Player.filter(
                    entity_id=e.entity_id).exists():
                await Player.create(player_id=db_member_id, codename=e.name, entity_id=e.entity_id)

    # update player rankings

    if ranked:
        logger.info(f"Updating player ranking for game {game.id}")

        if await ratinghelper.update_sm5_ratings(game):
            logger.info(f"Updated player rankings for game {game.id}")
        else:
            logger.error(f"Failed to update player rankings for game {game.id}")
    else:  # still need to add current_rating and previous_rating
        for entity_end in await game.entity_ends.filter(entity__type="player"):
            entity_id = (await entity_end.entity).entity_id
            if entity_id.startswith("@"):
                continue

            player = await Player.filter(entity_id=entity_id).first()

            try:
                entity_end.previous_rating_mu = player.sm5_mu
                entity_end.previous_rating_sigma = player.sm5_sigma
                entity_end.current_rating_mu = player.sm5_mu
                entity_end.current_rating_sigma = player.sm5_sigma
            except AttributeError:
                entity_end.previous_rating_mu = MU
                entity_end.previous_rating_sigma = SIGMA
                entity_end.current_rating_mu = MU
                entity_end.current_rating_sigma = SIGMA

            await entity_end.save()

    logger.info(f"Finished parsing {file_location} (game {game.id})")

    # precache the game so it's available immediately

    await precache_game("sm5", game.id)

    return game


async def parse_laserball_game(file_location: str) -> Optional[LaserballGame]:
    file = open(file_location, "r", encoding="utf-16")
    logger.info(f"Parsing {file_location}...")

    file_version = ""
    program_version = ""
    arena = ""

    mission_type = 0
    mission_name = ""
    start_time: str = ""
    mission_duration = 0

    teams: Teams = []
    entity_starts: EntityStarts = []
    events: Events = []
    player_states: PlayerStates = []
    scores: Scores = []
    entity_ends: EntityEnds = []

    laserball_stats: Dict[str, LaserballStats] = {}
    number_of_rounds = 0

    token_to_entity = {}

    # default values, will be changed later

    ranked = True
    ended_early = True  # will be changed to false if there's a mission end event

    linenum = 0
    while True:
        linenum += 1
        line = file.readline()
        if not line:
            break

        data = line.rstrip("\n").split("\t")
        match data[0]:  # switch on the first element of the line
            case ";":
                continue  # comment
            case "0":  # system info
                sentry_sdk.set_context("system_info",
                                       {"file_version": data[1], "program_version": data[2], "arena": data[3]})

                file_version = data[1]
                program_version = data[2]
                arena = data[3]
                logger.debug(
                    f"System Info: file version: {file_version}, program version: {program_version}, arena: {arena}")
            case "1":  # game info
                sentry_sdk.set_context("game_info",
                                       {"mission_type": data[1], "mission_name": data[2], "start_time": data[3],
                                        "mission_duration": data[4]})

                mission_type = int(data[1])
                mission_name = data[2]
                start_time = data[3]
                mission_duration = int(data[4])

                logger.debug(
                    f"Game Info: mission type: {mission_type}, mission name: {mission_name}, start time: {start_time}, mission duration: {mission_duration}")

                # check if game already exists
                if game := await LaserballGame.filter(start_time=start_time, arena=arena).first():
                    logger.warning(f"Game {game.id} already exists, skipping")
                    return game
                
                if mission_type != 28:
                    # only parse laserball games (mission type 28)

                    logger.warning(f"Game at {file_location} is not a Laserball game (mission type {mission_type}), skipping")
                    return None

            case "2":  # team info
                sentry_sdk.set_context("team_info", {"index": data[1], "name": data[2], "color_enum": data[3],
                                                     "color_name": data[4]})

                # TODO: remove hardcode purple (this is nessacery for now because purple's "color_name" is red for some reason)
                if data[2] == "Purple":
                    data[3] = 1
                    data[4] = "Purple"

                teams.append(
                    await Teams.create(index=int(data[1]), name=data[2], color_enum=data[3], color_name=data[4],
                                       real_color_name=element_to_color(data[4])))
                logger.debug(
                    f"Team Info: index: {data[1]}, name: {data[2]}, color enum: {data[3]}, color name: {data[4]}")
            case "3":  # entity start
                team = None

                for t in teams:
                    if t.index == int(data[5]):
                        team = t
                        break

                if team is None:
                    raise Exception("Team not found, invalid tdf file")

                # has index 9 (member id, but is only available when the setting is enabled)
                try:
                    member_id = int(data[9])
                except (ValueError, IndexError):
                    member_id = None

                name = data[4].strip()  # remove whitespace (some names have trailing whitespace for some reason)

                sentry_sdk.set_context(
                    "entity_start", {
                        "time": data[1],
                        "entity_id": data[2],
                        "type": data[3],
                        "name": data[4],
                        "team": data[5],
                        "level": data[6],
                        "role": data[7],
                        "battlesuit": data[8],
                        "member_id": member_id
                    }
                )

                entity_start = await EntityStarts.create(time=int(data[1]), entity_id=data[2], type=data[3], name=name,
                                                         team=team, level=int(data[6]), role=int(data[7]),
                                                         battlesuit=data[8], member_id=member_id)

                entity_starts.append(entity_start)
                token_to_entity[data[2]] = entity_start

                if entity_start.type == "player":
                    laserball_stats[entity_start.entity_id] = await LaserballStats.create(
                        entity=entity_start,
                        goals=0,
                        assists=0,
                        passes=0,
                        steals=0,
                        clears=0,
                        blocks=0,
                        started_with_ball=0,
                        times_stolen=0,
                        times_blocked=0,
                        passes_received=0,
                        shots_fired=0,
                        shots_hit=0
                    )

                logger.debug(
                    f"Entity Start: time: {data[1]}, entity id: {data[2]}, type: {data[3]}, name: {data[4]}, team: {data[5]}, level: {data[6]}, role: {data[7]}, battlesuit: {data[8]}")
            case "4":  # event
                sentry_sdk.set_context("event", {"time": data[1], "type": data[2], "arguments": data[3:]})

                # handle special laserball events

                event_type = EventType(data[2])
                args = data[3:]

                if event_type == EventType.GETS_BALL:
                    laserball_stats[args[0]].started_with_ball += 1
                    await laserball_stats[args[0]].save()
                elif event_type == EventType.GOAL:
                    laserball_stats[args[0]].goals += 1
                    laserball_stats[args[0]].shots_fired += 1
                    laserball_stats[args[0]].shots_hit += 1
                    await laserball_stats[args[0]].save()
                elif event_type == EventType.STEAL:
                    laserball_stats[args[0]].steals += 1
                    laserball_stats[args[0]].blocks += 1
                    laserball_stats[args[0]].shots_fired += 1
                    laserball_stats[args[0]].shots_hit += 1
                    laserball_stats[args[2]].times_stolen += 1
                    await laserball_stats[args[0]].save()
                    await laserball_stats[args[2]].save()
                elif event_type == EventType.CLEAR:
                    laserball_stats[args[0]].clears += 1
                    await laserball_stats[args[0]].save()
                elif event_type == EventType.BLOCK:
                    laserball_stats[args[0]].blocks += 1
                    laserball_stats[args[0]].shots_fired += 1
                    laserball_stats[args[0]].shots_hit += 1
                    laserball_stats[args[2]].times_blocked += 1
                    await laserball_stats[args[0]].save()
                    await laserball_stats[args[2]].save()
                elif event_type == EventType.PASS:
                    laserball_stats[args[0]].passes += 1
                    laserball_stats[args[0]].shots_fired += 1
                    laserball_stats[args[0]].shots_hit += 1
                    laserball_stats[args[2]].passes_received += 1
                    await laserball_stats[args[0]].save()
                    await laserball_stats[args[2]].save()
                elif event_type == EventType.ROUND_END:
                    number_of_rounds += 1
                elif event_type == EventType.MISS:
                    laserball_stats[args[0]].shots_fired += 1
                    await laserball_stats[args[0]].save()
                elif event_type == EventType.MISSION_END:  # game ended naturally
                    ended_early = False

                events.append(await Events.create(time=int(data[1]), type=event_type, arguments=json.dumps(data[3:])))

                logger.debug(f"Event: time: {data[1]}, type: {event_type}, arguments: {data[3:]}")
            case "5":  # score
                sentry_sdk.set_context("score", {"time": data[1], "entity": data[2], "old": data[3], "delta": data[4],
                                                 "new": data[5]})

                scores.append(await Scores.create(time=int(data[1]), entity=token_to_entity[data[2]], old=int(data[3]),
                                                  delta=int(data[4]), new=int(data[5])))
                logger.debug(
                    f"Score: time: {data[1]}, entity: {token_to_entity[data[2]]}, old: {data[3]}, delta: {data[4]}, new: {data[5]}")
            case "6":  # entity end
                sentry_sdk.set_context("entity_end",
                                       {"time": data[1], "entity": data[2], "type": data[3], "score": data[4]})

                entity_ends.append(await EntityEnds.create(time=int(data[1]), entity=token_to_entity[data[2]],
                                                           type=int(data[3]), score=int(data[4])))
                logger.debug(
                    f"Entity End: time: {data[1]}, entity: {token_to_entity[data[2]]}, type: {data[3]}, score: {data[4]}")
            case "9":  # player state
                sentry_sdk.set_context("player_state", {"time": data[1], "entity": data[2], "state": data[3]})

                player_states.append(await PlayerStates.create(time=int(data[1]), entity=token_to_entity[data[2]],
                                                               state=PlayerStateType(int(data[3]))))
                logger.debug(
                    f"Player State: time: {int(data[1])}, entity: {token_to_entity[data[2]]}, state: {data[3]}")

    # calculate assists (when a player passes to a player who scores)
    # so we need to find all the goals, and then find the pass that happened before it
    # this probably isn't 100% accurate but it's the best we can do

    logger.debug("Calculating assists")

    events_reversed = events[::-1]

    for e in events:
        if e.type == EventType.GOAL:
            # find the pass that happened before this goal
            for e2 in events_reversed:  # iterate backwards
                if e2.type == EventType.ROUND_START and e2.time < e.time:
                    break
                elif e2.type == EventType.PASS and e2.time < e.time:
                    # check if the pass was to the same player
                    if e2.arguments[2] == e.arguments[0]:
                        laserball_stats[e2.arguments[0]].assists += 1
                        await laserball_stats[e2.arguments[0]].save()
                        # add event after the goal event
                        events.append(
                            await Events.create(
                                time=e.time + 1,
                                type=EventType.ASSIST,
                                arguments=json.dumps([e2.arguments[0], "assists", e.arguments[0]])
                            )
                        )
                        break
                    else:
                        # wasn't the most recent pass so it's not an assist
                        break
                elif e2.type == EventType.STEAL and e2.time < e.time:
                    # if a steal happened before a valid pass, it can't be an assist
                    break

    # get the winner (goals scored is the only factor)

    team1_score = 0
    team1 = None
    team2_score = 0
    team2 = None

    i = 0
    for team in teams:
        if not team.color_name or not team.color_enum or team.name == "Neutral":
            continue

        if i == 0:  # found first team
            team1 = team
        else:  # found second team
            team2 = team

        # TODO: optimize this
        entities = await EntityStarts.filter(team=team, type="player").all()
        for e in entities:
            e_end = await EntityEnds.filter(entity__entity_id=e.entity_id).first()

            if i == 1:
                team1_score += e_end.score
            elif i == 2:
                team2_score += e_end.score

        i += 1

    if team1_score > team2_score:
        winner_model = team1
    elif team2_score > team1_score:
        winner_model = team2
    else:
        winner_model = None

    # calculate winner

    winner = None

    if winner_model is None:
        winner = None  # tie (draw)
    else:
        winner = winner_model.enum

    logger.debug(f"Winner: {winner}")

    # before creating the game, we need to make sure this game wasn't a false start
    # which means that game ended early and it lasted less than 3 minutes

    if ended_early and mission_duration < 3 * 60 * 1000:
        logger.warning("Game ended early and lasted less than 3 minutes, skipping")
        return None

    game = await LaserballGame.create(winner=Team.NONE, winner_color="none" if winner else "none",
                                      tdf_name=os.path.basename(file_location), file_version=file_version,
                                      ranked=ranked,
                                      software_version=program_version, arena=arena, mission_type=mission_type,
                                      mission_name=mission_name,
                                      start_time=datetime.strptime(start_time, "%Y%m%d%H%M%S"),
                                      mission_duration=mission_duration, ended_early=ended_early)

    sentry_sdk.set_context("game", {"id": game.id})

    await game.teams.add(*teams)
    await game.entity_starts.add(*entity_starts)
    await game.events.add(*events)
    await game.player_states.add(*player_states)
    await game.scores.add(*scores)
    await game.entity_ends.add(*entity_ends)
    await game.laserball_stats.add(*laserball_stats.values())

    await game.save()

    logger.debug("Inital game save complete")

    # determine winner

    await laserballhelper.update_winner(game)

    await game.save()

    # determine if the game should be ranked automatically

    # we don't have to check for exact team sizes because laserball is slightly more
    # flexible with team sizes

    team1_len = await game.entity_ends.filter(entity__team=team1, entity__type="player").count()
    team2_len = await game.entity_ends.filter(entity__team=team2, entity__type="player").count()

    logger.debug(f"Team 1 size: {team1_len}, Team 2 size: {team2_len}")

    # team size < 1

    if team1_len < 2 or team2_len < 2:
        logger.debug("One of the teams has less than 2 players, unranking game")
        ranked = False

    # check if there are any non-member players

    for e in entity_starts:
        if e.type == "player" and e.entity_id.startswith("@") and e.name == e.battlesuit:
            logger.debug(f"Found non-member player {e.name}, unranking game")
            ranked = False
            break

    # check if game was ended early (but not by elimination)

    # ended_early = if there's a mission end event (natural end by time or elim)
    # value set in event parsing

    game.ranked = ranked
    game.ended_early = ended_early

    sentry_sdk.set_context("game_info", {"ranked": ranked, "ended_early": ended_early})

    logger.debug(f"Ranked={ranked}, Ended Early={ended_early}")

    await game.save()

    logger.info("Resyncing player table")

    for e in entity_starts:
        if e.entity_id.startswith("@") and e.name == e.battlesuit:
            continue

        db_member_id = e.member_id if e.member_id else ""

        if e.type == "player":
            # update entity_id if it's empty
            if await Player.filter(codename=e.name).exists() and (
                    await Player.filter(codename=e.name).first()).entity_id == "":
                player = await Player.filter(codename=e.name).first()
                player.entity_id = e.entity_id
                player.player_id = db_member_id
                await player.save()
            # update player name if we have a new one and we have entity_id
            elif await Player.filter(entity_id=e.entity_id).exists() and (
                    await Player.filter(entity_id=e.entity_id).first()).codename != e.name:
                player = await Player.filter(entity_id=e.entity_id).first()
                player.name = e.name
                player.player_id = db_member_id
                await player.save()
            # update player_id if we have entity_id and don't have player_id
            elif await Player.filter(entity_id=e.entity_id).exists() and (
                    await Player.filter(entity_id=e.entity_id).first()).player_id == "":
                player = await Player.filter(entity_id=e.entity_id).first()
                player.player_id = db_member_id
                await player.save()
            # create new player if we don't have a name or entity_id
            elif not await Player.filter(codename=e.name).exists() and not await Player.filter(
                    entity_id=e.entity_id).exists():
                await Player.create(player_id=db_member_id, codename=e.name, entity_id=e.entity_id)

    # update player rankings

    if ranked:
        logger.info(f"Updating player ranking for game {game.id}")

        if await ratinghelper.update_laserball_ratings(game):
            logger.info(f"Updated player rankings for game {game.id}")
        else:
            logger.error(f"Failed to update player rankings for game {game.id}")
    else:  # still need to add current_rating and previous_rating
        for entity_end in await game.entity_ends.filter(entity__type="player"):
            entity_id = (await entity_end.entity).entity_id

            player = await Player.filter(entity_id=entity_id).first()

            try:
                entity_end.previous_rating_mu = player.laserball_mu
                entity_end.previous_rating_sigma = player.laserball_sigma
                entity_end.current_rating_mu = player.laserball_mu
                entity_end.current_rating_sigma = player.laserball_sigma
            except AttributeError:
                entity_end.previous_rating_mu = MU
                entity_end.previous_rating_sigma = SIGMA
                entity_end.current_rating_mu = MU
                entity_end.current_rating_sigma = SIGMA

            await entity_end.save()

    logger.info(f"Finished parsing {file_location} (game {game.id})")

    # precache the game so it's available immediately

    await precache_game("laserball", game.id)

    return game


async def parse_all_laserball_tdfs() -> None:  # iterate through laserball_tdf folder
    directory = os.listdir("laserball_tdf")
    directory.sort()  # first file is the oldest

    for file in directory:
        if file.endswith(".tdf"):
            logger.info(f"Parsing {file}")
            await parse_laserball_game(os.path.join("laserball_tdf", file))


async def parse_all_sm5_tdfs() -> None:  # iterate through sm5_tdf folder
    directory = os.listdir("sm5_tdf")
    directory.sort()  # first file is the oldest

    for file in directory:
        if file.endswith(".tdf"):
            logger.info(f"Parsing {file}")
            await parse_sm5_game(os.path.join("sm5_tdf", file))


async def parse_all_tdfs() -> None:
    await parse_all_sm5_tdfs()
    await parse_all_laserball_tdfs()


def get_arguments_from_event(arguments: list[str]) -> dict[str, str]:
    """Extracts specific semantic arguments from a list of event arguments.

    Args:
        arguments: The variable arguments of the event. Those are just the arguments that
            are part of the JSON payload, so this should be list with 1-3 strings.

    Returns:
        A dict with the arguments. Will currently always contain "action",
        "entity1", and "entity2".
        "action" is almost always non-empty, "entity1" is usually non-empty,
        "entity2" is often non-empty.
    """
    entity1 = ""
    entity2 = ""
    action = ""

    if not arguments:
        # There aren't known events with no arguments.
        logger.error("Found event with no arguments")
    else:
        if len(arguments) == 1:
            # This is a global event, such as "* Mission start *".
            action = arguments[0]
        else:
            entity1 = arguments[0]
            action = arguments[1]

            if len(arguments) > 2:
                entity2 = arguments[2]

                if len(arguments) > 3:
                    # There aren't known events with more than 3 arguments.
                    logger.error(f"Found event with more than 3 arguments: {str(arguments)}")

    return {
        "entity1": entity1,
        "action": action,
        "entity2": entity2,
    }


async def create_event_from_data(data: list[str]) -> Events:
    """Creates an Events object from arguments in an events table.

    Args:
        data: All strings in the line of the TDF file that define this event,
            so this should be a list of at least 4 strings (and the first one
            should be "4" to indicate that this is an event).
    """
    arguments = json.dumps(data[3:])

    if len(data) < 4:
        # There aren't really any events without arguments, so this is broken.
        # We should alert about that.
        return await Events.create(time=int(data[1]), type=EventType(data[2]), arguments=arguments)

    semantic_arguments = get_arguments_from_event(data[3:])

    return await Events.create(time=int(data[1]), type=EventType(data[2]), arguments=arguments,
                               entity1=semantic_arguments["entity1"], action=semantic_arguments["action"],
                               entity2=semantic_arguments["entity2"])


async def create_event(time_ms: int, type: EventType,
                       entity1: Optional[str] = None, action: Optional[str] = None,
                       entity2: Optional[str] = None) -> Events:
    """Creates an Events object from semantic arguments."""
    entity1 = entity1 if entity1 else ""
    action = action if action else ""
    entity2 = entity2 if entity2 else ""

    return await Events.create(time=time_ms, type=type,
                               entity1=entity1, action=action, entity2=entity2,
                               arguments=json.dumps({}))
