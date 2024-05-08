import json
import os
from datetime import datetime
from typing import List, Dict

from sanic.log import logger

from db.game import EntityEnds, EntityStarts, Events, Scores, PlayerStates, Teams
from db.laserball import LaserballGame, LaserballStats
from db.player import Player
from db.sm5 import SM5Game, SM5Stats
from db.types import EventType, PlayerStateType, Team
from helpers import ratinghelper


def element_to_color(element: str) -> str:
    conversion = {
        "Fire": "Red",
        "Ice": "Blue",
        "Earth": "Green",
        "None": "None"
    }

    return conversion[element]


async def parse_sm5_game(file_location: str) -> SM5Game:
    file = open(file_location, "r", encoding="utf-16")

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
    ended_early = False  # will be changed to false if there's a mission end event

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
                file_version = data[1]
                program_version = data[2]
                arena = data[3]
                logger.debug(
                    f"System Info: file version: {file_version}, program version: {program_version}, arena: {arena}")
            case "1":  # game info
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

            case "2":  # team info
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

                # has index 8
                try:
                    member_id = int(data[8])
                except ValueError:
                    member_id = None

                name = data[4].strip()  # remove whitespace (some names have trailing whitespace for some reason)

                entity_start = await EntityStarts.create(time=int(data[1]), entity_id=data[2], type=data[3], name=name,
                                                         team=team, level=int(data[6]), role=int(data[7]),
                                                         battlesuit=data[8], member_id=member_id)

                entity_starts.append(entity_start)
                token_to_entity[data[2]] = entity_start
            case "4":  # event
                # okay but why is event type a string
                events.append(await create_event_from_data(data))

                if EventType(data[2]) == EventType.MISSION_END:  # game ended naturally
                    ended_early = False

                logger.debug(f"Event: time: {data[1]}, type: {EventType(data[2])}, arguments: {data[3:]}")
            case "5":  # score
                scores.append(await Scores.create(time=int(data[1]), entity=token_to_entity[data[2]], old=int(data[3]),
                                                  delta=int(data[4]), new=int(data[5])))
                logger.debug(
                    f"Score: time: {data[1]}, entity: {token_to_entity[data[2]]}, old: {data[3]}, delta: {data[4]}, new: {data[5]}")
            case "6":  # entity end
                entity_ends.append(await EntityEnds.create(time=int(data[1]), entity=token_to_entity[data[2]],
                                                           type=int(data[3]), score=int(data[4])))
                logger.debug(
                    f"Entity End: time: {data[1]}, entity: {token_to_entity[data[2]]}, type: {data[3]}, score: {data[4]}")
            case "7":  # sm5 stats
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
                player_states.append(await PlayerStates.create(time=int(data[1]), entity=token_to_entity[data[2]],
                                                               state=PlayerStateType(int(data[3]))))
                logger.debug(
                    f"Player State: time: {int(data[1])}, entity: {token_to_entity[data[2]]}, state: {data[3]}")

    # getting the winner

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

    game = await SM5Game.create(winner=None, winner_color="none", tdf_name=os.path.basename(file_location),
                                file_version=file_version, ranked=ranked,
                                software_version=program_version, arena=arena, mission_type=mission_type,
                                mission_name=mission_name,
                                start_time=datetime.strptime(start_time, "%Y%m%d%H%M%S"),
                                mission_duration=mission_duration, ended_early=ended_early)

    await game.teams.add(*teams)
    await game.entity_starts.add(*entity_starts)
    await game.events.add(*events)
    await game.player_states.add(*player_states)
    await game.scores.add(*scores)
    await game.entity_ends.add(*entity_ends)
    await game.sm5_stats.add(*sm5_stats)

    await game.save()

    logger.debug("Inital game save complete")

    # winner determination

    winner = None
    red_score = await game.get_team_score(Team.RED)
    green_score = await game.get_team_score(Team.GREEN)
    if red_score > green_score:
        winner = Team.RED
    elif red_score < green_score:
        winner = Team.GREEN
    else:  # tie or no winner or something crazy happened
        winner = None

    game.winner = winner
    game.winner_color = winner.value if winner else "none"
    await game.save()

    logger.debug(f"Winner: {game.winner_color}")

    # determine if the game should be ranked automatically

    # 5 < team size < 7 and teams are not of unequal size (ratings are not tested for unequal team sizes)

    team1_len = await game.entity_ends.filter(entity__team=team1, entity__type="player").count()
    team2_len = await game.entity_ends.filter(entity__team=team2, entity__type="player").count()

    if team1_len > 7 or team2_len > 7 or team1_len < 5 or team2_len < 5 or team1_len != team2_len:
        ranked = False

    # check if there are any non-member players

    for e in entity_starts:
        if e.type == "player" and e.entity_id.startswith("@") and e.name == e.battlesuit:
            ranked = False
            break

    # check if game was ended early (but not by elimination)

    # ended_early = if there's a mission end event (natural end by time or elim)
    # value set in event parsing

    logger.debug(f"Ranked={ranked}, Ended Early={ended_early}")

    game.ranked = ranked
    game.ended_early = ended_early

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

            entity_end.previous_rating_mu = player.sm5_mu
            entity_end.previous_rating_sigma = player.sm5_sigma
            entity_end.current_rating_mu = player.sm5_mu
            entity_end.current_rating_sigma = player.sm5_sigma

            await entity_end.save()

    logger.info(f"Finished parsing {file_location} (game {game.id})")

    return game


async def parse_laserball_game(file_location: str) -> LaserballGame:
    file = open(file_location, "r", encoding="utf-16")

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
                file_version = data[1]
                program_version = data[2]
                arena = data[3]
                logger.debug(
                    f"System Info: file version: {file_version}, program version: {program_version}, arena: {arena}")
            case "1":  # game info
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

            case "2":  # team info
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

                # has index 8
                try:
                    member_id = int(data[8])
                except ValueError:
                    member_id = None

                name = data[4].strip()  # remove whitespace (some names have trailing whitespace for some reason)

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
                scores.append(await Scores.create(time=int(data[1]), entity=token_to_entity[data[2]], old=int(data[3]),
                                                  delta=int(data[4]), new=int(data[5])))
                logger.debug(
                    f"Score: time: {data[1]}, entity: {token_to_entity[data[2]]}, old: {data[3]}, delta: {data[4]}, new: {data[5]}")
            case "6":  # entity end
                entity_ends.append(await EntityEnds.create(time=int(data[1]), entity=token_to_entity[data[2]],
                                                           type=int(data[3]), score=int(data[4])))
                logger.debug(
                    f"Entity End: time: {data[1]}, entity: {token_to_entity[data[2]]}, type: {data[3]}, score: {data[4]}")
            case "9":  # player state
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

    index = 1

    for t in teams:
        if not t.color_name or not t.color_enum or t.name == "Neutral":
            continue

        if index == 1:
            team1 = t
        else:  # 2
            team2 = t

        entities = await EntityStarts.filter(team=t, type="player").all()
        for e in entities:
            e_end = await EntityEnds.filter(entity__entity_id=e.entity_id).first()

            if index == 1:
                team1_score += e_end.score
            elif index == 2:  # 2
                team2_score += e_end.score

        index += 1

    if team1_score > team2_score:
        winner_model = team1
    elif team2_score > team1_score:
        winner_model = team2
    else:
        winner_model = None

    # may need to be adjusted for more team colors/names

    red_colors = ["Solid Red", "Fire", "Red"]
    blue_colors = ["Solid Blue", "Ice", "Earth", "Blue", "Solid Green", "Green"]

    if winner_model is None:
        winner = None  # tie (draw)
    elif winner_model.color_name in red_colors:
        winner = Team.RED
    elif winner_model.color_name in blue_colors:
        winner = Team.BLUE
    else:
        raise Exception("Invalid team color")  # or can't find correct team color

    logger.debug(f"Winner: {winner}")

    # before creating the game, we need to make sure this game wasn't a false start
    # which means that game ended early and it lasted less than 3 minutes

    if ended_early and mission_duration < 3 * 60 * 1000:
        logger.warning("Game ended early and lasted less than 3 minutes, skipping")
        return None

    game = await LaserballGame.create(winner=winner, winner_color=winner.value if winner else "none",
                                      tdf_name=os.path.basename(file_location), file_version=file_version,
                                      ranked=ranked,
                                      software_version=program_version, arena=arena, mission_type=mission_type,
                                      mission_name=mission_name,
                                      start_time=datetime.strptime(start_time, "%Y%m%d%H%M%S"),
                                      mission_duration=mission_duration, ended_early=ended_early)

    await game.teams.add(*teams)
    await game.entity_starts.add(*entity_starts)
    await game.events.add(*events)
    await game.player_states.add(*player_states)
    await game.scores.add(*scores)
    await game.entity_ends.add(*entity_ends)
    await game.laserball_stats.add(*laserball_stats.values())

    await game.save()

    logger.debug("Inital game save complete")

    # determine if the game should be ranked automatically

    # we don't have to check for exact team sizes because laserball is slightly more
    # flexible with team sizes

    team1_len = await game.entity_ends.filter(entity__team=team1, entity__type="player").count()
    team2_len = await game.entity_ends.filter(entity__team=team2, entity__type="player").count()

    # 1 < team size

    if team1_len < 1 or team2_len < 1:
        ranked = False

    # check if there are any non-member players

    for e in entity_starts:
        if e.type == "player" and e.entity_id.startswith("@") and e.name == e.battlesuit:
            ranked = False
            break

    # check if game was ended early (but not by elimination)

    # ended_early = if there's a mission end event (natural end by time or elim)
    # value set in event parsing

    game.ranked = ranked
    game.ended_early = ended_early

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
                entity_end.previous_rating_mu = 25
                entity_end.previous_rating_sigma = 25 / 3
                entity_end.current_rating_mu = 25
                entity_end.current_rating_sigma = 25 / 3

            await entity_end.save()

    logger.info(f"Finished parsing {file_location} (game {game.id})")

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
