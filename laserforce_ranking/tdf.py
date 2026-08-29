from pathlib import Path
from laserforce_ranking.models.types import EntityType, EventType, EntityEndType, PlayerStateType, IntRole, SITES, SITE_TIMEZONES, TeamType
from laserforce_ranking.models.game import Game, Team, EntityStart, Event, EntityEnd, PlayerState, Score
from laserforce_ranking.models.sm5 import SM5Stats, SM5Game
from laserforce_ranking.models.laserball import LaserballStats
from typing import Optional, List, Dict
from .rating import SM5_RANK_VERSION, update_sm5_rankings, MU, SIGMA, BLANK_RATING
from laserforce_ranking.models.player import Player
import aiohttp
from django.db import transaction
from playwright.async_api import async_playwright
from asgiref.sync import sync_to_async
import os
import traceback

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
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://laserforce.spoo.uk/api/game/{game_type}/{i}/tdf") as resp:
                    if resp.status == 404 or "404 - Not Found" in (await resp.text()):
                        current_breaks += 1
                        if current_breaks >= break_amount:
                            break
                        else:
                            i += 1
                            continue
                    
                    data = await resp.json()

                    # save tdf to disk
                    tdf_name = f"sm5_{data['id']}.tdf"
                    tdf_path = Path(f"tdfs/{tdf_name}")

                    with open(tdf_path, "w", encoding="utf-16") as f:
                        f.write(data["tdf"])

                    # process tdf
            i += 1


async def scrape_lfstats_tdf(site_id: Optional[str] = None):
    # scrape https://lfstats.com/games?scope=social&center=<center>
    # pagninated list 
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()

        print(f"Scraping {site_id}")
        if site_id:
            await page.goto(f"https://lfstats.com/games?scope=social&center={site_id}")
        else:
            await page.goto(f"https://lfstats.com/games?scope=social")

        # Wait for the page to load
        await page.wait_for_selector(".p-2.align-middle.whitespace-nowrap")

        # print page content

        # click on start_date to sort by oldest first

        started = await page.query_selector("thead[data-slot='table-header'] > tr > th:nth-child(3) > button")
        if started:
            await started.click()
            await page.wait_for_timeout(2000)

        page_num = 0
        while True:
            # Find all links to tdfs
            links = await page.query_selector_all(".p-2.align-middle.whitespace-nowrap a")
            hrefs = [(await link.get_attribute("href")).split("/")[-1] for link in links]

            print(f"Found {len(hrefs)} tdfs on page {page_num} for {site_id}")
            for href in hrefs:
                # check if we already have this tdf
                tdf_name = f"{href}.tdf"
                tdf_path = Path(f"tdfs/{tdf_name}")

                if os.path.exists(tdf_path):
                    print(f"Already have {tdf_name}, skipping")
                    continue

                # get tdf from link
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://lfstats-modern-archive.s3.us-west-1.amazonaws.com/{href}.tdf") as tdf_resp:
                        if tdf_resp.status == 404 or "404 - Not Found" in (await tdf_resp.text()):
                            continue

                        data = await tdf_resp.text()

                        # save tdf to disk

                        if not tdf_path.exists():
                            os.makedirs(tdf_path.parent, exist_ok=True)

                        # Remove extra blank lines
                        data = "\n".join(line for line in data.splitlines() if line.strip())

                        with open(tdf_path, "w", encoding="utf-16") as f:
                            f.write(data)

            # Check if there is a next page, if so, navigate to it
            next_button = await page.query_selector("div.flex.items-center.justify-between > div.flex.gap-2 > button:nth-child(2)")
            if next_button:
                await next_button.click()
                await page.wait_for_timeout(1000)  # Wait for the next page to load
                page_num += 1 
            else:
                print(f"Finished scraping {site_id}")
                break

        await browser.close()

async def mass_parse_tdfs():
    tdf_dir = Path("tdfs")
    for tdf_file in tdf_dir.glob("*.tdf"):
        if await parse_tdf(tdf_file):
            return

# tdf parsing

async def parse_tdf(file_location: Path):
    # first we will process the general information about the game, then we will
    # process the more specific game type
    # current types allowed: sm5, laserball

    print(f"Parsing {file_location}")

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
                site = data[3] # site id, ex: 4-43
            case "1": # mission info
                mission_type = int(data[1]) # site dependant enum
                mission_name = data[2] # mission name in system, dependant on site
                start_time = data[3] # ex: 20260719204954 -> 2026-07-19 20:49:54
                mission_duration = int(data[4] if len(data) > 4 else 900000) # how long the game can last if it doesn't end early, in milliseconds
                penalty_amount = int(data[5] if len(data) > 5 else -1000) # score added for each penalty (ex: 0, -1000)

                # convert to datetime with timezone
                start_time_formatted = f"{start_time[0:4]}-{start_time[4:6]}-{start_time[6:8]} {start_time[8:10]}:{start_time[10:12]}:{start_time[12:14]}"

                # add timezone for site
                timezone = SITE_TIMEZONES.get(site, "UTC")
                start_time_formatted += f" {timezone}"

                # check if we already have this game in the database, if so, skip it
                if await SM5Game.objects.filter(site_id=site, start_time=start_time_formatted).aexists(): \
                    #or await LaserballGame.objects.filter(site_id=site, start_time=start_time_formatted).aexists():
                    print(f"Game {file_location.name} already exists in the database, skipping")
                    return
            case "2": # team info
                index = int(data[1])
                name = data[2]
                color_enum = int(data[3])
                color_name = data[4]
                real_color_name = element_to_color(color_name)

                teams[index] = Team(
                    index=index,
                    name=name,
                    color_enum=color_enum,
                    color_name=color_name,
                    real_color_name=real_color_name
                )
            case "3": # entity start
                time = int(data[1]) # ms since start
                entity_id = data[2] # ex: #ZRbsz (member) or @71 (battlesuit/base)
                entity_type = EntityType(data[3])
                name = data[4]
                team_index = int(data[5])
                level = int(data[6])
                role = int(data[7]) # "category"
                battlesuit = data[8] if len(data) > 8 else None
                member_id = data[9] if len(data) > 9 else None

                team = teams.get(team_index)

                entity_starts[entity_id] = EntityStart(
                    time=time,
                    entity_id=entity_id,
                    type=entity_type,
                    name=name,
                    team=team,
                    level=level,
                    role=role,
                    battlesuit=battlesuit,
                    member_id=member_id
                )
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
                entity_end_type = EntityEndType(int(data[3]))
                score = int(data[4])

                entity_start = entity_starts.get(entity_id)

                entity_end = EntityEnd(
                    time=time,
                    entity=entity_start,
                    type=entity_end_type,
                    score=score
                )

                entity_ends.append(entity_end)
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

                entity_start = entity_starts.get(entity_id)
        
                player_states.append(PlayerState(
                    time=time,
                    entity=entity_start,
                    state=player_state_type
                ))

    # combine entity_ends.score onto team.score

    for entity_end in entity_ends:
        if entity_end.entity.team:
            if entity_end.entity.team.score is None:
                entity_end.entity.team.score = 0
            entity_end.entity.team.score += entity_end.score

    # seperate into team1 and team2
    # there is no specification which color team1 or team2 is

    team1 = None
    team2 = None

    index = 1

    for t in teams.values():
        if not t.color_name or not t.color_enum or t.name == "Neutral":
            continue

        if index == 1:
            team1 = t
        else:  # 2
            team2 = t

        index += 1

    # get team sizes

    team1_size = len([e for e in entity_starts.values() if e.team == team1 and e.type == EntityType.PLAYER])
    team2_size = len([e for e in entity_starts.values() if e.team == team2 and e.type == EntityType.PLAYER])

    if force_ended_early:
        print("Game ended early, skipping ranking") # TODO: log
        return
    
    # players

    for entity_id, e in entity_starts.items():
        # is a player and logged in
        if entity_id.startswith("@") and e.name == e.battlesuit:
            continue

        db_member_id = e.member_id if e.member_id else None

        if e.type == EntityType.PLAYER:
            # update player name if we have a new one and we have entity_id
            if await Player.objects.filter(entity_id=entity_id).aexists() and (
                    await Player.objects.filter(entity_id=entity_id).afirst()).codename != e.name:
                player = await Player.objects.filter(entity_id=entity_id).afirst()
                player.codename = e.name
                player.player_id = db_member_id
                await player.asave()
            # update player_id if we have entity_id and don't have player_id
            elif await Player.objects.filter(entity_id=entity_id).aexists() and (
                    await Player.objects.filter(entity_id=entity_id).afirst()).player_id == "":
                player = await Player.objects.filter(entity_id=entity_id).afirst()
                player.player_id = db_member_id

                split_ = db_member_id.split("-")
                home_site = f"{split_[0]}-{split_[1]}" if len(split_) > 1 else None
                player.home_site = home_site

                await player.asave()
            # create new player if we don't have a name or entity_id
            elif not await Player.objects.filter(codename=e.name).aexists() and not await Player.objects.filter(
                    entity_id=entity_id).aexists():
                
                if db_member_id:
                    split_ = db_member_id.split("-")
                    home_site = f"{split_[0]}-{split_[1]}" if len(split_) > 1 else None
                else:
                    home_site = None

                ratings = {
                    "global": BLANK_RATING,
                }
                ratings[site] = BLANK_RATING

                await Player.objects.acreate(player_id=db_member_id, codename=e.name, entity_id=entity_id, home_site=home_site, ratings=ratings)

    # find game type

    base_args = {
        "file_location": file_location,
        "site_id": site,
        "tdf_name": file_location.name,
        "file_version": file_version,
        "software_version": program_version,
        "mission_type": mission_type,
        "mission_name": mission_name,
        "force_ended_early": force_ended_early,
        "start_time": start_time_formatted,
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


async def process_sm5(
    file_location: Path,
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
    teams: Dict[int, Team],
    entity_starts: Dict["str", EntityStart],
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
    try:
        # special points

        # key: player entity id, value: special points
        # this is needed because tdf doesn't save the ending special points
        # and leaderboards usually have this info
        # we'll update this dict as we parse events and then save the final values to the database when we parse the entity end events
        player_special_points: Dict[str, int] = {}
        # key: player entity id, value: whether the player can gain specials (False if heavy or has rapid fire on)
        player_can_gain_specials: Dict[str, bool] = {}

        for entity_id, entity_start in entity_starts.items():
            if entity_start.type == EntityType.PLAYER:
                # if this is a player, determine if they can gain specials (heavies can't gain specials and scouts can't gain specials until they get rapid fire)

                player_special_points[entity_id] = 0
                if entity_start.role == IntRole.HEAVY:
                    player_can_gain_specials[entity_id] = False
                else:
                    player_can_gain_specials[entity_id] = True

        for event in events:
            # handle special points
            if player_can_gain_specials.get(event.entity1, True): # if player can gain specials (not heavy or doesn't have rapid fire on)
                match event.type:
                    # give specials
                    case EventType.DAMAGED_OPPONENT | EventType.DOWNED_OPPONENT:
                        # only enemies (damaged/downed opponent still is used for teammates)
                        if entity_starts[event.entity1].team.name != entity_starts[event.entity2].team.name:
                            player_special_points[event.entity1] = min(player_special_points.get(event.entity1, 0) + 1, 99)
                    case EventType.MISSILE_DOWN_OPPONENT:
                        if entity_starts[event.entity1].team.name != entity_starts[event.entity2].team.name:
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
                if entity_starts[event.entity2].role == IntRole.SCOUT:
                    # rapid fire turned off, specials can be gained again
                    player_can_gain_specials[event.entity2] = True
        
        # create sm5 game

        game = SM5Game(
            site_id=site_id,
            tdf_name=tdf_name,
            file_version=file_version,
            software_version=software_version,
            mission_type=mission_type,
            mission_name=mission_name,
            ranked=True,
            force_ended_early=force_ended_early,
            start_time=start_time,
            mission_duration=mission_duration,
            penalty_amount=penalty_amount,
            last_team_standing=None,
            team1_size=team1_size,
            team2_size=team2_size
        )

        await game.asave()

        print(f"Saving game {game.id} to database")
        for team in teams.values():
            team.game = game
            await team.asave()
        await game.teams.aset(teams.values())
        for entity_start in entity_starts.values():
            entity_start.game = game
            await entity_start.asave()
            await sync_to_async(entity_start.team.entity_starts.add)(entity_start)
            await entity_start.team.asave() # save team to database first
        await game.entity_starts.aset(entity_starts.values())
        for event in events:
            event.game = game
            await event.asave()
        await game.events.aset(events)
        for score in scores:
            score.game = game
            score.entity.game = game
            await score.entity.asave() # save entity to database first
            await score.asave()
        await game.scores.aset(scores)
        for entity_end in entity_ends:
            entity_end.game = game
            entity_end.entity.entity_end = entity_end
            await entity_end.asave()
        await game.entity_ends.aset(entity_ends)
        for player_state in player_states:
            player_state.game = game
            await player_state.asave()
        await game.player_states.aset(player_states)
        for sm5_stat in sm5_stats:
            sm5_stat.special_points = player_special_points.get(sm5_stat.entity.entity_id, 0)
            sm5_stat.entity = entity_starts[sm5_stat.entity.entity_id]
            sm5_stat.entity_end = sm5_stat.entity.entity_end
            sm5_stat.game = game
            await sm5_stat.asave()
        await game.sm5_stats.aset(sm5_stats)

        # determine if the game should be ranked automatically

        ranked = True

        # 5 < team size < 7 and teams are not of unequal size (ratings are not tested for unequal team sizes)

        team1_len = await game.entity_ends.filter(entity__team=team1, entity__type="player").acount()
        team2_len = await game.entity_ends.filter(entity__team=team2, entity__type="player").acount()

        if team1_len > 7 or team2_len > 7 or team1_len < 5 or team2_len < 5 or team1_len != team2_len:
            ranked = False

        # also check that our roles are correct
        # ex: a standard sm5 team has 1 commander, 1 heavy, 1 scout, 1 medic, 1 ammo, and 1-3 scouts

        # for each team
        for t in teams.values():
            total_count = 0
            commander_count = 0
            heavy_count = 0
            scout_count = 0
            ammo_count = 0
            medic_count = 0

            for e in entity_starts.values():
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

        game.ranked = ranked

        # get last team_standing
        alive_player_count = {}

        async for entity in game.entity_starts.filter(type=EntityType.PLAYER).prefetch_related("team").all():
            player = await SM5Stats.objects.filter(entity__id=entity.id).afirst()

            if player and player.lives_left > 0:
                alive_player_count[entity.team.color_enum] = alive_player_count.get(entity.team.color_enum, 0) + 1

        # If there isn't exactly one team with alive players at the end, this wasn't an elimination game.
        if len(alive_player_count) == 1:
            entity_start = await game.entity_starts.filter(team__color_enum=list(alive_player_count.keys())[0]).afirst()
            game.last_team_standing = await sync_to_async(lambda: entity_start.team)()


        # doubles %

        game.team1_double_percent = await game._get_team_doubles_percent(team1)
        game.team2_double_percent = await game._get_team_doubles_percent(team2)

        # winner

        # get all teams in the game.
        teams = await game.get_teams()

        scores = {team: team.score for team in teams}

        # adjust scores if a team was eliminated.
        if game.last_team_standing:
            scores[game.last_team_standing] += 10000

        # determine the winner based on the updated scores.
        max_score = max(scores.values())
        winning_teams = [team for team, score in scores.items() if score == max_score]

        if len(winning_teams) == 1:
            winner = winning_teams[0]
        else: # Tie or no clear winner
            winner = None

        game.winner = winner

        # rankings

        if ranked:
            if await update_sm5_rankings(game):
                pass#logger.info(f"Updated player rankings for game {game.id}")
            else:
                pass#logger.error(f"Failed to update player rankings for game {game.id}")
        else:  # still need to add current_rating and previous_rating
            async for entity_end in game.entity_ends.filter(entity__type=EntityType.PLAYER).all():
                entity_start = await sync_to_async(lambda: entity_end.entity)()
                entity_id = entity_start.entity_id
                if entity_id.startswith("@"):
                    entity_end.ratings = {
                        "global": {
                            "mu": MU,
                            "sigma": SIGMA
                        },
                        "global_role": {
                            "mu": MU,
                            "sigma": SIGMA
                        },
                        "site": {
                            "mu": MU,
                            "sigma": SIGMA
                        },
                        "site_role": {
                            "mu": MU,
                            "sigma": SIGMA
                        }
                    }

                player = await Player.objects.filter(entity_id=entity_id).afirst()

                try:
                    global_ratings = await player.get_rating()
                    global_role_ratings = await player.get_rating(role=entity_start.role)
                    site_ratings = await player.get_rating(site=game.site_id)
                    site_role_ratings = await player.get_rating(role=entity_start.role, site=game.site_id)

                    entity_end.ratings = {
                        "global": {
                            "mu": global_ratings.mu,
                            "sigma": global_ratings.sigma
                        },
                        "global_role": {
                            "mu": global_role_ratings.mu,
                            "sigma": global_role_ratings.sigma
                        },
                        "site": {
                            "mu": site_ratings.mu,
                            "sigma": site_ratings.sigma
                        },
                        "site_role": {
                            "mu": site_role_ratings.mu,
                            "sigma": site_role_ratings.sigma
                        }
                    }
                except AttributeError:
                    entity_end.ratings = {
                        "global": {
                            "mu": MU,
                            "sigma": SIGMA
                        },
                        "global_role": {
                            "mu": MU,
                            "sigma": SIGMA
                        },
                        "site": {
                            "mu": MU,
                            "sigma": SIGMA
                        },
                        "site_role": {
                            "mu": MU,
                            "sigma": SIGMA
                        }
                    }

                await entity_end.asave()

        await game.asave()
    except BaseException as e:
        print(f"Error processing game {file_location.name} or got cut off. Deleting...")
        traceback.print_exc()
        if game is not None and game.pk is not None:
            await game.adelete()
        # delete all teams, entity_starts, events, scores, entity_ends, player_states, sm5_stats
        for team in teams.values():
            if team.pk is not None:
                await team.adelete()
        for entity_start in entity_starts.values():
            if entity_start.pk is not None:
                await entity_start.adelete()
        for event in events:
            if event.pk is not None:
                await event.adelete()
        for score in scores:
            if score.pk is not None:
                await score.adelete()
        for entity_end in entity_ends:
            if entity_end.pk is not None:
                await entity_end.adelete()
        for player_state in player_states:
            if player_state.pk is not None:
                await player_state.adelete()
        for sm5_stat in sm5_stats:
            if sm5_stat.pk is not None:
                await sm5_stat.adelete()
        raise e
        

async def process_laserball(
    file_location: Path,
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