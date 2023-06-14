from db.models import Player, Events, EventType, Teams, EntityStarts, SM5Game, EntityEnds, Scores, IntRole, SM5Stats
from datetime import datetime
from objects import Team
from sanic.log import logger
import json
import os

async def parse_sm5_game(file_location: str) -> SM5Game:
    file = open(file_location, "r", encoding="utf-16")

    file_version = ""
    program_version = ""
    arena = ""

    mission_type = 0
    mission_name = ""
    start_time: str = ""
    mission_duration = 0

    teams = []
    entity_starts = []
    events = []
    scores = []
    entity_ends = []
    sm5_stats = []

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
                    return game

            case "2": # team info
                teams.append(await Teams.create(index=int(data[1]), name=data[2], color_enum=data[3], color_name=data[4]))
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
        raise Exception("Edge case: draw")

    # may need to be adjusted for more team colors/names

    red_colors = ["Solid Red", "Fire", "Red"]
    green_colors = ["Solid Blue", "Ice", "Earth", "Blue", "Solid Green", "Green"]

    if winner_model.color_name in red_colors:
        winner = Team.RED
    elif winner_model.color_name in green_colors:
        winner = Team.GREEN
    else:
        raise Exception("Invalid team color") # or can't find correct team color
    
    # determine if the game should be ranked automatically

    ranked = True
    ended_early = False

    # first check if either team has more than 7 players or less than 5 players

    team1_len = await EntityEnds.filter(entity__team=team1, entity__type="player").count()
    team2_len = await EntityEnds.filter(entity__team=team2, entity__type="player").count()

    if team1_len > 7 or team2_len > 7 or team1_len < 5 or team2_len < 5:
        ranked = False

    # check if game was ended early (but not by elimination)

    # if it didn't end naturally
    if not await EntityEnds.filter(type=EventType.MISSION_END).exists():
        ranked = False
        ended_early = True


    game = await SM5Game.create(winner=winner, tdf_name=os.path.basename(file_location), file_version=file_version, ranked=ranked,
                                software_version=program_version, arena=arena, mission_type=mission_type, mission_name=mission_name,
                                start_time=datetime.strptime(start_time, "%Y%m%d%H%M%S"), mission_duration=mission_duration, ended_early=ended_early)
    
    await game.teams.add(*teams)
    await game.entity_starts.add(*entity_starts)
    await game.events.add(*events)
    await game.scores.add(*scores)
    await game.entity_ends.add(*entity_ends)
    await game.sm5_stats.add(*sm5_stats)

    await game.save()


async def parse_all_tdfs() -> None: # iterate through sm5_tdf folder
    directory = os.listdir("sm5_tdf")
    directory.sort() # first file is the oldest

    for file in directory:
        if file.endswith(".tdf"):
            logger.info(f"Parsing {file}")
            await parse_sm5_game(os.path.join("sm5_tdf", file))