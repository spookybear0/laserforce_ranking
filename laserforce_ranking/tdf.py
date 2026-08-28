from pathlib import Path
from laserforce_ranking.models.types import EntityType, EventType, EntityEndType, PlayerStateType, IntRole
from laserforce_ranking.models.game import Game, Team, EntityStart, Event, EntityEnd, PlayerState, Score
from laserforce_ranking.models.sm5 import SM5Stats, SM5Game
from laserforce_ranking.models.laserball import LaserballStats
from typing import Optional, List, Dict
from .rating import SM5_RANK_VERSION, update_sm5_rankings, MU, SIGMA
from laserforce_ranking.models.player import Player
import aiohttp
from bs4 import BeautifulSoup

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

# tdf importing/uploading

async def import_legacy_tdf():
    """
    Imports tdfs from the old laserforce_ranking website

    Both sm5 and laserball
    """
    
    # https://laserforce.spoo.uk/api/game/<type>/<id>

    break_amount = 5 # how many 404s in a row to break the loop, since there are gaps in the ids
    current_breaks = 0
    for game_type in ["sm5", "laserball"]:
        i = 1
        while True:
            print(i, game_type)
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://laserforce.spoo.uk/api/game/{game_type}/{i}/tdf") as resp:
                    if resp.status == 404 or "404 - Not Found" in (await resp.text()):
                        current_breaks += 1
                        if current_breaks >= break_amount:
                            break
                        else:
                            i += 1
                            continue
                    
                    print(await resp.text())
                    data = await resp.json()

                    # save tdf to disk
                    tdf_name = f"sm5_{data['id']}.tdf"
                    tdf_path = Path(f"tdfs/{tdf_name}")

                    with open(tdf_path, "w", encoding="utf-16") as f:
                        f.write(data["tdf"])

                    # process tdf
            i += 1


async def scrape_lfstats_tdf():
    SITES = {
        "Loveland": "4-19",
        "Brisbane": "1-1",
        "Syracuse": "4-23",
        # skip invasion
        "St George": "4-2",
        "Auckland Wairau": "3-3",
        "Detroit": "4-6",
        "Lasergame Říčany": "20-7",
        "PowerLaser Stuttgart": "21-8",
        "LaserTag Darmstadt": "21-70",
        "Wollongong Revolution": "1-58",
        "Auckland Game Over": "3-7",
        "Peterborough": "7-2",
        "Cheltanham": "7-13",
        "Sydney Underworld": "1-64",
        "Huddersfield": "7-8",
        "Lasergame Beroun": "20-18"
    }

    # scrape https://lfstats.com/games?scope=social&center=<center>
    # pagninated list 

    async with aiohttp.ClientSession() as session:
        for center, site_id in SITES.items():
            print(f"Scraping {center} ({site_id})")
            async with session.get(f"https://lfstats.com/games?scope=social&center={site_id}") as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                # find all links to tdfs
                links = soup.find_all(class_="text-blue-700")
                print(links)

# tdf parsing

async def parse_tdf(file_location: Path):
    # first we will process the general information about the game, then we will
    # process the more specific game type
    # current types allowed: sm5, laserball

    file = open(file_location, "r", encoding="utf-16")

    # read line by line

    teams = {} # index: Team
    entity_starts = {} # entity_id: EntityStart
    events = []
    scores = []
    entity_ends = []
    sm5_stats = []
    player_states = []

    force_ended_early = True # if the game ended early, this will be set to false if the game ended naturally

    while True:
        line = file.readline()
        if not line:
            break

        data = line.rstrip("\n").split("\t")

        # example of a line: 0	2.006	8.704	4-23
        match data[0]:
            case ";":
                # this is a comment, ignore it
                continue
            case "0": # general info
                file_version = data[1]
                program_version = data[2]
                site = data[3] # site id, ex: 4-43 (4 is north america)
            case "1": # mission info
                mission_type = int(data[1]) # site dependant enum
                mission_name = data[2] # mission name in system, dependant on site
                start_time = data[3] # ex: 20260719204954 -> 2026-07-19 20:49:54
                mission_duration = int(data[4]) # milliseconds
                penalty_amount = int(data[5]) # score added for each penalty (ex: 0, -1000)
            case "2": # team info
                index = int(data[1])
                name = data[2]
                color_enum = int(data[3])
                color_name = data[4]
                real_color_name = element_to_color(color_name)

                teams.append(Team(
                    index=index,
                    name=name,
                    color_enum=color_enum,
                    color_name=color_name,
                    real_color_name=real_color_name
                ))
            case "3": # entity start
                time = int(data[1]) # ms since start
                entity_id = data[2] # ex: #ZRbsz (member) or @71 (battlesuit/base)
                entity_type = EntityType(data[3])
                name = data[4]
                team_index = int(data[5])
                level = int(data[6])
                role = int(data[7]) # "category"
                battlesuit = data[8]
                member_id = data[9] if len(data) > 9 else None

                team = teams.get(team_index)

                entity_starts.append(EntityStart(
                    time=time,
                    entity_id=entity_id,
                    type=entity_type,
                    name=name,
                    team=team,
                    level=level,
                    role=role,
                    battlesuit=battlesuit,
                    member_id=member_id
                ))
            case "4": # event
                time = int(data[1])
                event_type = EventType(data[2])
                entity1 = data[3] if len(data) > 3 else ""
                action = data[4] if len(data) > 4 else ""
                entity2 = data[5] if len(data) > 5 else ""

                if event_type == EventType.MISSION_END:  # game ended naturally
                    force_ended_early = False

                events.append(Event(
                    time=time,
                    type=event_type,
                    entity1=entity1,
                    action=action,
                    entity2=entity2
                ))       
            case "5": # score deltas
                time = int(data[1])
                entity_id = data[2]
                old = int(data[3])
                delta = int(data[4])
                new = int(data[5])

                entity_start = entity_starts.get(entity_id)

                scores.append(Score(
                    time=time,
                    entity=entity_start,
                    old=old,
                    delta=delta,
                    new=new
                ))
            case "6": # entity end
                time = int(data[1])
                entity_id = data[2]
                entity_end_type = EntityEndType(data[3])
                score = int(data[4])

                entity_start = entity_starts.get(entity_id)

                entity_end = EntityEnd(
                    time=time,
                    entity=entity_start,
                    type=entity_end_type,
                    score=score
                )

                entity_ends.append(entity_end)
                entity_start.entity_end = entity_end
            case "7": # sm5 stats
                entity_id = data[1]
                shots_hit = int(data[2])
                shots_fired = int(data[3])
                times_zapped = int(data[4])
                times_missiled = int(data[5])
                missile_hits = int(data[6])
                nukes_detonated = int(data[7])
                nukes_activated = int(data[8])
                nuke_cancels = int(data[9])
                medic_hits = int(data[10])
                own_medic_hits = int(data[11])
                medic_nukes = int(data[12])
                scout_rapid_fires = int(data[13])
                life_boosts = int(data[14])
                ammo_boosts = int(data[15])
                lives_left = int(data[16])
                shots_left = int(data[17])
                penalties = int(data[18])
                shot_3_hits = int(data[19])
                own_nuke_cancels = int(data[20])
                shot_opponent = int(data[21])
                shot_team = int(data[22])
                missiled_opponent = int(data[23])
                missiled_team = int(data[24])

                entity_start = entity_starts.get(entity_id)
                entity_end = entity_start.entity_end

                sm5_stats.append(SM5Stats(
                    entity=entity_start,
                    entity_end=entity_end,
                    shots_hit=shots_hit,
                    shots_fired=shots_fired,
                    times_zapped=times_zapped,
                    times_missiled=times_missiled,
                    missile_hits=missile_hits,
                    nukes_detonated=nukes_detonated,
                    nukes_activated=nukes_activated,
                    nuke_cancels=nuke_cancels,
                    medic_hits=medic_hits,
                    own_medic_hits=own_medic_hits,
                    medic_nukes=medic_nukes,
                    scout_rapid_fires=scout_rapid_fires,
                    life_boosts=life_boosts,
                    ammo_boosts=ammo_boosts,
                    lives_left=lives_left,
                    shots_left=shots_left,
                    penalties=penalties,
                    shot_3_hits=shot_3_hits,
                    own_nuke_cancels=own_nuke_cancels,
                    shot_opponent=shot_opponent,
                    shot_team=shot_team,
                    missiled_opponent=missiled_opponent,
                    missiled_team=missiled_team
                ))
            # 8 is unknown
            case "9": # player state
                time = int(data[1])
                entity_id = data[2]
                player_state_type = PlayerStateType(int(data[3]))
        
                player_states.append(PlayerState(
                    time=time,
                    entity=entity_start,
                    state=player_state_type
                ))

    # seperate into team1 and team2
    # there is no specification which color team1 or team2 is

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

    # get team sizes

    team1_size = len([e for e in entity_starts if e.team == team1 and e.type == EntityType.PLAYER])
    team2_size = len([e for e in entity_starts if e.team == team2 and e.type == EntityType.PLAYER])

    if force_ended_early:
        print("Game ended early, skipping ranking") # TODO: log
        return

    # find game type

    base_args = {
        "site_id": site,
        "tdf_name": file_location.name,
        "file_version": file_version,
        "software_version": program_version,
        "mission_type": mission_type,
        "mission_name": mission_name,
        "force_ended_early": force_ended_early,
        "start_time": start_time,
        "mission_duration": mission_duration,
        "penalty_amount": penalty_amount,
        "teams": teams,
        "entity_starts": entity_starts,
        "events": events,
        "scores": scores,
        "entity_ends": entity_ends,
        "player_states": player_states,
        "team1": team1,
        "team2": team2,
        "team1_size": team1_size,
        "team2_size": team2_size
    }
   
    if mission_type == 5: # sm5
        await process_sm5(
            **base_args,
            sm5_stats=sm5_stats,
        )
    elif mission_type == 28: # laserball
        await process_laserball(
            **base_args
        )
    else:
        print(f"Unknown mission type: {mission_type} ({mission_name})")
        return

    for e in entity_starts:
        # is a player and logged in
        if e.entity_id.startswith("@") and e.name == e.battlesuit:
            continue

        db_member_id = e.member_id if e.member_id else ""

        if e.type == EntityType.PLAYER:
            # update player name if we have a new one and we have entity_id
            if await Player.filter(entity_id=e.entity_id).exists() and (
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


async def process_sm5(
    site_id: str,
    tdf_name: str,
    file_version: str,
    software_version: str,
    mission_type: int,
    mission_name: str,
    force_ended_early: bool,
    start_time: str,
    mission_duration: int,
    penalty_amount: int,
    teams: List[Team],
    entity_starts: List[EntityStart],
    events: List[Event],
    scores: List[Score],
    entity_ends: List[EntityEnd],
    player_states: List[PlayerState],
    team1: Team,
    team2: Team,
    team1_size: int,
    team2_size: int,
    sm5_stats: List[SM5Stats],
):
    # special points

    # key: player entity id, value: special points
    # this is needed because tdf doesn't save the ending special points
    # and leaderboards usually have this info
    # we'll update this dict as we parse events and then save the final values to the database when we parse the entity end events
    player_special_points: Dict[str, int] = {}
    # key: player entity id, value: whether the player can gain specials (False if heavy or has rapid fire on)
    player_can_gain_specials: Dict[str, bool] = {}

    for entity_start in entity_starts:
        if entity_start.type == EntityType.PLAYER:
            # if this is a player, determine if they can gain specials (heavies can't gain specials and scouts can't gain specials until they get rapid fire)

            player_special_points[entity_start.entity_id] = 0
            if entity_start.role == IntRole.HEAVY:
                player_can_gain_specials[entity_start.entity_id] = False
            else:
                player_can_gain_specials[entity_start.entity_id] = True

    for event in events:
        # handle special points
        if player_can_gain_specials.get(event.entity1, True): # if player can gain specials (not heavy or doesn't have rapid fire on)
            match event.type:
                # give specials
                case EventType.DAMAGED_OPPONENT | EventType.DOWNED_OPPONENT:
                    # only enemies (damaged/downed opponent still is used for teammates)
                    if entity_starts[event.entity1].team != entity_starts[event.entity1].team:
                        player_special_points[event.entity1] = min(player_special_points.get(event.entity1, 0) + 1, 99)
                case EventType.MISSILE_DOWN_OPPONENT:
                    if entity_starts[event.entity1].team != entity_starts[event.entity1].team:
                        player_special_points[event.entity1] = min(player_special_points.get(event.entity1, 0) + 2, 99)

                # remove specials
                case EventType.ACTIVATE_NUKE:
                    player_special_points[event.entity1] = min(player_special_points.get(event.entity1, 0) - 20, 99)
                case EventType.AMMO_BOOST:
                    player_special_points[event.entity1] = min(player_special_points.get(event.entity1, 0) - 15, 99)
                case EventType.LIFE_BOOST:
                    player_special_points[event.entity1] = min(player_special_points.get(event.entity1, 0) - 10, 99)

        # scouts can get sp from bases even with rapid
        if event.type in [EventType.DESTROY_BASE, EventType.MISSILE_BASE_DESTROY, EventType.BASE_AWARDED] and entity_starts[event.entity1].role != IntRole.HEAVY:
            player_special_points[event.entity1] = min(player_special_points.get(event.entity1, 0) + 5, 99)

        # scout activated rapid
        if event.type == EventType.ACTIVATE_RAPID_FIRE:
            # rapid fire turned on, specials can't be gained until it's turned off
            player_special_points[event.entity1] = min(player_special_points.get(event.entity1, 0) - 10, 99)
            player_can_gain_specials[event.entity1] = False

        # scout deactivated rapid from being resupplied ammo or lives
        if event.type in [EventType.RESUPPLY_AMMO, EventType.RESUPPLY_LIVES]:
            if entity_starts[event.entity1].role == IntRole.SCOUT:
                # rapid fire turned off, specials can be gained again
                player_can_gain_specials[event.entity1] = True

    # determine if the game should be ranked automatically

    ranked = True

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
            if e.type == EntityType.PLAYER and e.team == t:
                total_count += 1
                if e.role == IntRole.COMMANDER:
                    commander_count += 1
                elif e.role == IntRole.HEAVY:
                    heavy_count += 1
                elif e.role == IntRole.SCOUT:
                    scout_count += 1
                elif e.role == IntRole.AMMO: # sometimes we have 2 ammos, but for ranking purposes we only want games with 1
                    ammo_count += 1
                elif e.role == IntRole.MEDIC:
                    medic_count += 1

        if total_count == 0:  # probably a neutral team
            continue

        if commander_count != 1 or heavy_count != 1 or ammo_count != 1 or medic_count != 1 or scout_count < 1 or scout_count > 3:
            ranked = False

    
    
    # create sm5 game

    game = SM5Game(
        site_id=site_id,
        tdf_name=tdf_name,
        file_version=file_version,
        software_version=software_version,
        mission_type=mission_type,
        mission_name=mission_name,
        ranked=ranked,
        force_ended_early=force_ended_early,
        start_time=start_time,
        mission_duration=mission_duration,
        penalty_amount=penalty_amount,
        teams=teams,
        entity_starts=entity_starts,
        events=events,
        player_states=player_states,
        scores=scores,
        entity_ends=entity_ends,
        sm5_stats=sm5_stats,
        last_team_standing=None
    )

    # get last team_standing
    alive_player_count = {}
    entities = await game.entity_starts.all()

    for entity in entities:
        player = await SM5Stats.filter(entity__id=entity.id).first()

        if player and player.lives_left > 0:
            alive_player_count[(await entity.team).enum] = True

    # If there isn't exactly one team with alive players at the end, this wasn't an elimination game.
    if len(alive_player_count) == 1:
        game.last_team_standing = await game.entity_starts.filter(team__enum=list(alive_player_count.keys())[0]).first().team
    
    

    # doubles %

    game.team1_double_percent = await game._get_team_doubles_percent(team1)
    game.team2_double_percent = await game._get_team_doubles_percent(team2)

    # rankings

    if ranked:

        if await update_sm5_rankings(game):
            pass#logger.info(f"Updated player rankings for game {game.id}")
        else:
            pass#logger.error(f"Failed to update player rankings for game {game.id}")
    else:  # still need to add current_rating and previous_rating
        for entity_end in await game.entity_ends.filter(entity__type=EntityType.PLAYER).all():
            entity_start = entity_end.entity
            entity_id = entity_start.entity_id
            if entity_id.startswith("@"):
                continue

            player = await Player.objects.filter(entity_id=entity_id).afirst()

            try:
                # global
                entity_end.previous_rating_mu = await player.get_rating().mu
                entity_end.previous_rating_sigma = await player.get_rating().sigma
                entity_end.current_rating_mu = await player.get_rating().mu
                entity_end.current_rating_sigma = await player.get_rating().sigma

                entity_end.previous_role_rating_mu = await player.get_rating(role=entity_start.role).mu
                entity_end.previous_role_rating_sigma = await player.get_rating(role=entity_start.role).sigma
                entity_end.current_role_rating_mu = await player.get_rating(role=entity_start.role).mu
                entity_end.current_role_rating_sigma = await player.get_rating(role=entity_start.role).sigma

                # site-specific
                entity_end.previous_site_rating_mu = await player.get_rating(site=game.site_id).mu
                entity_end.previous_site_rating_sigma = await player.get_rating(site=game.site_id).sigma
                entity_end.current_site_rating_mu = await player.get_rating(site=game.site_id).mu
                entity_end.current_site_rating_sigma = await player.get_rating(site=game.site_id).sigma

                entity_end.previous_site_role_rating_mu = await player.get_rating(role=entity_start.role, site=game.site_id).mu
                entity_end.previous_site_role_rating_sigma = await player.get_rating(role=entity_start.role, site=game.site_id).sigma
                entity_end.current_site_role_rating_mu = await player.get_rating(role=entity_start.role, site=game.site_id).mu
                entity_end.current_site_role_rating_sigma = await player.get_rating(role=entity_start.role, site=game.site_id).sigma
            except AttributeError:
                entity_end.previous_rating_mu, entity_end.current_rating_mu, \
                entity_end.previous_site_rating_mu, entity_end.current_site_rating_mu, \
                entity_end.previous_role_rating_mu, entity_end.current_role_rating_mu, \
                entity_end.previous_site_role_rating_mu, entity_end.current_site_role_rating_mu = MU
                
                entity_end.previous_rating_mu, entity_end.current_rating_mu, \
                entity_end.previous_site_rating_mu, entity_end.current_site_rating_mu, \
                entity_end.previous_role_rating_mu, entity_end.current_role_rating_mu, \
                entity_end.previous_site_role_rating_mu, entity_end.current_site_role_rating_mu = SIGMA

            await entity_end.save()

    await game.save()

async def process_laserball(
    site_id: str,
    tdf_name: str,
    file_version: str,
    software_version: str,
    mission_type: int,
    mission_name: str,
    force_ended_early: bool,
    start_time: str,
    mission_duration: int,
    penalty_amount: int,
    teams: List[Team],
    entity_starts: List[EntityStart],
    events: List[Event],
    scores: List[Score],
    entity_ends: List[EntityEnd],
    team1: Team,
    team2: Team,
    team1_size: int,
    team2_size: int,
    player_states: List[PlayerState]
):
    # ranking
    pass