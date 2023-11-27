from db.models import Player, Events, EventType, Teams, EntityStarts, SM5Game, EntityEnds, Scores, IntRole, SM5Stats, LaserballGame, LaserballStats
from typing import List, Dict
from datetime import datetime
from objects import Team
from sanic.log import logger
from helpers import ratinghelper
import aiohttp
import json
import os


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

    teams: Teams = []
    entity_starts: List[EntityStarts] = []
    events: Events = []
    scores: Scores = []
    entity_ends: List[EntityEnds] = []
    sm5_stats: List[SM5Stats] = []

    token_to_entity = {}

    linenum = 0
    while True:
        linenum += 1
        line = file.readline()
        if not line:
            break

        data = line.rstrip("\n").split("\t")
        match data[0]: # switch on the first element of the line
            case ";":
                continue # comment
            case "0": # system info
                file_version = data[1]
                program_version = data[2]
                arena = data[3]
            case "1": # game info
                mission_type = int(data[1])
                mission_name = data[2]
                start_time = data[3]
                mission_duration = int(data[4])

                # check if game already exists
                if game := await SM5Game.filter(start_time=start_time, arena=arena).first():
                    logger.warn(f"Game {game.id} already exists, skipping")
                    return game

            case "2": # team info
                teams.append(await Teams.create(index=int(data[1]), name=data[2], color_enum=data[3], color_name=data[4], real_color_name=element_to_color(data[4])))
            case "3": # entity start
                team = None

                for t in teams:
                    if t.index == int(data[5]):
                        team = t
                        break
                
                if team is None:
                    raise Exception("Team not found, invalid tdf file")
                
                entity_start = await EntityStarts.create(time=int(data[1]), entity_id=data[2], type=data[3], name=data[4],
                                        team=team, level=int(data[6]), role=int(data[7]), battlesuit=data[8])

                entity_starts.append(entity_start)
                token_to_entity[data[2]] = entity_start
            case "4": # event
                # okay but why is this a thing
                if data[2] == "0B03": # base awarded
                    data[2] = 2819 # keeping my system in integers
                events.append(await Events.create(time=int(data[1]), type=EventType(int(data[2])), arguments=json.dumps(data[3:])))
            case "5": # score
                scores.append(await Scores.create(time=int(data[1]), entity=token_to_entity[data[2]], old=int(data[3]),
                    delta=int(data[4]), new=int(data[5])))
            case "6": # entity end
                entity_ends.append(await EntityEnds.create(time=int(data[1]), entity=token_to_entity[data[2]],
                    type=int(data[3]), score=int(data[4])))
            case "7": # sm5 stats
                sm5_stats.append(await SM5Stats.create(entity=token_to_entity[data[1]],
                    shots_hit=int(data[2]), shots_fired=int(data[3]), times_zapped=int(data[4]), times_missiled=int(data[5]),
                    missile_hits=int(data[6]), nukes_detonated=int(data[7]), nukes_activated=int(data[8]), nuke_cancels=int(data[9]),
                    medic_hits=int(data[10]), own_medic_hits=int(data[11]), medic_nukes=int(data[12]), scout_rapid_fires=int(data[13]),
                    life_boosts=int(data[14]), ammo_boosts=int(data[15]), lives_left=int(data[16]), shots_left=int(data[17]),
                    penalties=int(data[18]), shot_3_hits=int(data[19]), own_nuke_cancels=int(data[20]), shot_opponent=int(data[21]),
                    shot_team=int(data[22]), missiled_opponent=int(data[23]), missiled_team=int(data[24])))

    # getting the winner

    team1 = None
    team2 = None

    index = 1

    for t in teams:
        if not t.color_name or not t.color_enum or t.name == "Neutral":
            continue
        
        if index == 1:
            team1 = t
        else: # 2
            team2 = t

        index += 1

    # default values, will be changed later

    ranked = True
    ended_early = False

    game = await SM5Game.create(winner=None, winner_color="none", tdf_name=os.path.basename(file_location), file_version=file_version, ranked=ranked,
                                software_version=program_version, arena=arena, mission_type=mission_type, mission_name=mission_name,
                                start_time=datetime.strptime(start_time, "%Y%m%d%H%M%S"), mission_duration=mission_duration, ended_early=ended_early)
    
    await game.teams.add(*teams)
    await game.entity_starts.add(*entity_starts)
    await game.events.add(*events)
    await game.scores.add(*scores)
    await game.entity_ends.add(*entity_ends)
    await game.sm5_stats.add(*sm5_stats)

    await game.save()

    # winner determination

    winner = None
    if await game.get_red_score() > await game.get_green_score():
        winner = Team.RED
    elif await game.get_red_score() < await game.get_green_score():
        winner = Team.GREEN
    else: # tie or no winner or something crazy happened
        winner = None

    game.winner = winner
    game.winner_color = winner.value if winner else "none"
    await game.save()

    # determine if the game should be ranked automatically

    # 5 < team size < 7

    team1_len = await game.entity_ends.filter(entity__team=team1, entity__type="player").count()
    team2_len = await game.entity_ends.filter(entity__team=team2, entity__type="player").count()

    if team1_len > 7 or team2_len > 7 or team1_len < 5 or team2_len < 5:
        ranked = False

    # check if there are any non-member players

    for e in entity_starts:
        if e.type == "player" and e.entity_id.startswith("@") and e.name == e.battlesuit:
            ranked = False
            break

    # check if game was ended early (but not by elimination)

    # if it didn't end naturally
    if not await game.events.filter(type=EventType.MISSION_END).exists():
        ranked = False
        ended_early = True

    game.ranked = ranked
    game.ended_early = ended_early

    await game.save()

    logger.info("Resyncing player table")

    # add new players to the database

    # TODO: find a way to get the player_id from the tdf file
    # or from the token (ipl_id which is the same as the entity_id)

    for e in entity_starts:
        # is a player and logged in
        if e.type == "player" and not (e.entity_id.startswith("@") and e.name == e.battlesuit):
            # update ipl_id if it's empty
            if await Player.filter(codename=e.name).exists() and (await Player.filter(codename=e.name).first()).ipl_id == "":
                player = await Player.filter(codename=e.name).first()
                player.ipl_id = e.entity_id
                await player.save()
            # update player name if we have a new one and we have ipl_id
            elif await Player.filter(ipl_id=e.entity_id).exists() and (await Player.filter(ipl_id=e.entity_id).first()).codename != e.name:
                player = await Player.filter(ipl_id=e.entity_id).first()
                player.name = e.name
                await player.save()
            # create new player if we don't have a name or ipl_id
            elif not await Player.filter(codename=e.name).exists() and not await Player.filter(ipl_id=e.entity_id).exists():
                await Player.create(player_id="", codename=e.name, ipl_id=e.entity_id)

    # update player rankings

    if ranked:
        logger.info(f"Updating player ranking for game {game.id}")

        if await ratinghelper.update_sm5_ratings(game):
            logger.info(f"Updated player rankings for game {game.id}")
        else:
            logger.error(f"Failed to update player rankings for game {game.id}")
    else: # still need to add current_rating and previous_rating
        for entity_end in await game.entity_ends.filter(entity__type="player"):
            entity_id = (await entity_end.entity).entity_id

            player = await Player.filter(ipl_id=entity_id).first()
            
            if entity_id.startswith("#"): # member
                entity_end.previous_rating_mu = player.sm5_mu
                entity_end.previous_rating_sigma = player.sm5_sigma
                entity_end.current_rating_mu = player.sm5_mu
                entity_end.current_rating_sigma = player.sm5_sigma
            else: # "@", non member
                entity_end.previous_rating_mu = ratinghelper.MU
                entity_end.previous_rating_sigma = ratinghelper.SIGMA
                entity_end.current_rating_mu = ratinghelper.MU
                entity_end.current_rating_sigma = ratinghelper.SIGMA

            await entity_end.save()

    logger.info(f"Finished parsing {file_location} (game {game.id})")

async def parse_laserball_game(file_location: str):
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
    scores: Scores = []
    entity_ends: EntityEnds = []

    laserball_stats: Dict[str, LaserballStats] = {}
    number_of_rounds = 0

    token_to_entity = {}

    linenum = 0
    while True:
        linenum += 1
        line = file.readline()
        if not line:
            break

        data = line.rstrip("\n").split("\t")
        match data[0]: # switch on the first element of the line
            case ";":
                continue # comment
            case "0": # system info
                file_version = data[1]
                program_version = data[2]
                arena = data[3]
            case "1": # game info
                mission_type = int(data[1])
                mission_name = data[2]
                start_time = data[3]
                mission_duration = int(data[4])

                # check if game already exists
                if game := await LaserballGame.filter(start_time=start_time, arena=arena).first():
                    return game

            case "2": # team info
                teams.append(await Teams.create(index=int(data[1]), name=data[2], color_enum=data[3], color_name=data[4], real_color_name=element_to_color(data[4])))
            case "3": # entity start
                team = None

                for t in teams:
                    if t.index == int(data[5]):
                        team = t
                        break
                
                if team is None:
                    raise Exception("Team not found, invalid tdf file")
                
                entity_start = await EntityStarts.create(time=int(data[1]), entity_id=data[2], type=data[3], name=data[4],
                                        team=team, level=int(data[6]), role=int(data[7]), battlesuit=data[8])

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
                        passes_received=0
                    )
            case "4": # event
                # handle special laserball events

                event_type = EventType(int(data[2]))
                args = data[3:]

                if event_type == EventType.GETS_BALL:
                    laserball_stats[args[0]].started_with_ball += 1
                    await laserball_stats[args[0]].save()
                elif event_type == EventType.GOAL:
                    laserball_stats[args[0]].goals += 1
                    await laserball_stats[args[0]].save()
                elif event_type == EventType.STEAL:
                    laserball_stats[args[0]].steals += 1
                    laserball_stats[args[2]].times_stolen += 1
                    await laserball_stats[args[0]].save()
                    await laserball_stats[args[2]].save()
                elif event_type == EventType.CLEAR:
                    laserball_stats[args[0]].clears += 1
                    await laserball_stats[args[0]].save()
                elif event_type == EventType.BLOCK:
                    laserball_stats[args[0]].blocks += 1
                    laserball_stats[args[2]].times_blocked += 1
                    await laserball_stats[args[0]].save()
                    await laserball_stats[args[2]].save()
                elif event_type == EventType.PASS:
                    laserball_stats[args[0]].passes += 1
                    laserball_stats[args[2]].passes_received += 1
                    await laserball_stats[args[0]].save()
                    await laserball_stats[args[2]].save()
                elif event_type == EventType.ROUND_END:
                    number_of_rounds += 1

                events.append(await Events.create(time=int(data[1]), type=event_type, arguments=json.dumps(data[3:])))
            case "5": # score
                scores.append(await Scores.create(time=int(data[1]), entity=token_to_entity[data[2]], old=int(data[3]),
                    delta=int(data[4]), new=int(data[5])))
            case "6": # entity end
                entity_ends.append(await EntityEnds.create(time=int(data[1]), entity=token_to_entity[data[2]],
                    type=int(data[3]), score=int(data[4])))
                
    # calculate assists (when a player passes to a player who scores)
    # so we need to find all the goals, and then find the pass that happened before it

    for e in events:
        if e.type == EventType.GOAL:
            # find the pass that happened before this goal
            events_reversed = events[::-1]
            for e2 in events_reversed:
                if e2.type == EventType.PASS and e2.time < e.time:
                    # check if the pass was to the same player
                    if e2.arguments[2] == e.arguments[0]:
                        laserball_stats[e2.arguments[0]].assists += 1
                        await laserball_stats[e2.arguments[0]].save()
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
        else: # 2
            team2 = t

        entities = await EntityStarts.filter(team=t, type="player").all()
        for e in entities:
            e_end = await EntityEnds.filter(entity__entity_id=e.entity_id).first()

            if index == 1:
                team1_score += e_end.score
            elif index == 2: # 2
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
        winner = None # tie (draw)
    elif winner_model.color_name in red_colors:
        winner = Team.RED
    elif winner_model.color_name in blue_colors:
        winner = Team.BLUE
    else:
        raise Exception("Invalid team color") # or can't find correct team color
    
    # default values, will be changed later

    ranked = True
    ended_early = False

    game = await LaserballGame.create(winner=winner, winner_color=winner.value if winner else "none", tdf_name=os.path.basename(file_location), file_version=file_version, ranked=ranked,
                                software_version=program_version, arena=arena, mission_type=mission_type, mission_name=mission_name,
                                start_time=datetime.strptime(start_time, "%Y%m%d%H%M%S"), mission_duration=mission_duration, ended_early=ended_early)
    
    await game.teams.add(*teams)
    await game.entity_starts.add(*entity_starts)
    await game.events.add(*events)
    await game.scores.add(*scores)
    await game.entity_ends.add(*entity_ends)
    await game.laserball_stats.add(*laserball_stats.values())

    await game.save()

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

    # if it didn't end naturally

    if not await game.events.filter(type=EventType.MISSION_END).exists():
        ranked = False
        ended_early = True
    
    game.ranked = ranked
    game.ended_early = ended_early

    await game.save()

    for e in entity_starts:
        if e.type == "player":
            # update ipl_id if it's empty
            if await Player.filter(codename=e.name).exists() and (await Player.filter(codename=e.name).first()).ipl_id == "":
                player = await Player.filter(codename=e.name).first()
                player.ipl_id = e.entity_id
                await player.save()
            # update player name if we have a new one and we have ipl_id
            elif await Player.filter(ipl_id=e.entity_id).exists() and (await Player.filter(ipl_id=e.entity_id).first()).codename != e.name:
                player = await Player.filter(ipl_id=e.entity_id).first()
                player.name = e.name
                await player.save()
            # create new player if we don't have a name or ipl_id
            elif not await Player.filter(codename=e.name).exists() and not await Player.filter(ipl_id=e.entity_id).exists():
                await Player.create(player_id="", codename=e.name, ipl_id=e.entity_id)

    # update player rankings

    if ranked:
        logger.info(f"Updating player ranking for game {game.id}")

        if await ratinghelper.update_laserball_ratings(game):
            logger.info(f"Updated player rankings for game {game.id}")
        else:
            logger.error(f"Failed to update player rankings for game {game.id}")
    else: # still need to add current_rating and previous_rating
        for entity_end in await game.entity_ends.filter(entity__type="player"):
            entity_id = (await entity_end.entity).entity_id

            player = await Player.filter(ipl_id=entity_id).first()
            
            entity_end.previous_rating_mu = player.laserball_mu
            entity_end.previous_rating_sigma = player.laserball_sigma
            entity_end.current_rating_mu = player.laserball_mu
            entity_end.current_rating_sigma = player.laserball_sigma

            await entity_end.save()

    logger.info(f"Finished parsing {file_location} (game {game.id})")

async def parse_all_laserball_tdfs() -> None: # iterate through laserball_tdf folder
    directory = os.listdir("laserball_tdf")
    directory.sort() # first file is the oldest

    for file in directory:
        if file.endswith(".tdf"):
            logger.info(f"Parsing {file}")
            await parse_laserball_game(os.path.join("laserball_tdf", file))

async def parse_all_sm5_tdfs() -> None:  # iterate through sm5_tdf folder
    directory = os.listdir("sm5_tdf")
    directory.sort() # first file is the oldest

    for file in directory:
        if file.endswith(".tdf"):
            logger.info(f"Parsing {file}")
            await parse_sm5_game(os.path.join("sm5_tdf", file))



async def parse_all_tdfs() -> None:
    await parse_all_sm5_tdfs()
    await parse_all_laserball_tdfs()