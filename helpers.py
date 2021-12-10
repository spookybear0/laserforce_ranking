from types import CodeType
import mysql # type: ignore
from typing import List, Union, Tuple
from config import config # type: ignore
from objects import Player, Game, Role, RankMMR, Rank, GamePlayer, Team # type: ignore
from glob import player_cron_log, rank_cron_log # type: ignore
import laserforce # type: ignore
import pymysql
import asyncio
from elo import get_win_chance, update_elo

sql = None

def average(to_average: Union[List, Tuple]):
    return sum(to_average) / len(to_average)

# iron: 0.60, 60%
# bronze: 0.75, 75%
# silver: 1.0, 100% (average)
# gold: 1.15, 115%
# diamond: 1.25, 125%
# immortal: 1.35, 135%
# lasermaster: top 5 average mmr

def format_sql(to_format) -> List:
    final = []
    for i in to_format:
        final.append(i[0])
    return final

async def get_top_100_by_role(role: Role, amount: int=100, start: int=0):
    q = await sql.fetchall(f"SELECT codename, player_id FROM players ORDER BY ranking_{role.value} DESC LIMIT {amount} OFFSET {start}")
    return list(q)

async def get_top_100(amount: int=100, start: int=0):
    q = await sql.fetchall(f"SELECT codename, player_id FROM players ORDER BY LENGTH(player_id), player_id ASC LIMIT {amount} OFFSET {start}")
    return list(q)

async def get_total_players():
    q = await sql.fetchone("SELECT COUNT(*) FROM players")
    return q[0]

async def get_total_games():
    q = await sql.fetchone("SELECT COUNT(*) FROM games")
    return q[0]

async def get_total_games_played():
    q = await sql.fetchone("SELECT COUNT(*) FROM game_players")
    return q[0]

async def get_mmr(player_id: str):
    q = await sql.fetchall("SELECT ranking_scout, ranking_heavy, ranking_commander, ranking_medic, ranking_ammo FROM `players` WHERE `player_id` = %s", (player_id))
    all_mmr = list(q[0]) # format
    try:
        while True:
            all_mmr.remove(0.0)
    except ValueError:
        pass
    if all_mmr == []:
        return 0
    mmr = average(all_mmr)
    return mmr

async def get_games_played(player_id: str):
    q = await sql.fetchall("SELECT * FROM `game_players` WHERE `player_id` = %s", (player_id))
    q = format_sql(q) # format
    return len(q)

async def recalculate_elo():
    base_elo = 1200
    
    # reset elo
    await sql.execute("UPDATE `players` SET `elo` = %s", (base_elo,))
    
    i = 1
    while True:
        try:
            game = await fetch_game(i)
        except IndexError:
            print("Done recalculating")
            break
        
        k = 512
        
        if game.winner == Team.RED:
            winner_int = 0
        else: # is green
            winner_int = 1
        
        game.red, game.green = update_elo(game.red, game.green, winner_int, k) # update elo
        game.players = [*game.red, *game.green]
        
        for player in game.players:
            player.game_id = game.id
        
            await sql.execute("UPDATE `players` SET `elo` = %s WHERE `player_id` = %s", (player.elo, player.player_id))
        
        i += 1

async def legacy_ranking_cron():
    roles = list(Role)
    id = 1
    while True:
        rank_cron_log(f"LEGACY: Searching for player at index {id}")
        try:
            player_id = await sql.fetchone("SELECT player_id FROM `players` WHERE `id` = %s", id)
        except:
            break
        try:
            player_id = player_id[0]
        except TypeError:
            break
        # mmr cron
        rank_cron_log(f"LEGACY: Updating rank for: {player_id}")
        val_list = []
        for role in roles:
            try:
                score = await get_my_ranking_score(role, player_id)
            except ZeroDivisionError: # no games
                score = 0

            val_list.append(score)
        try:
            await sql.execute(f"UPDATE players SET ranking_scout = %s, ranking_heavy = %s, ranking_commander = %s, ranking_ammo = %s, ranking_medic = %s WHERE player_id = %s", (val_list[0], val_list[1], val_list[2], val_list[3], val_list[4], player_id))
        except pymysql.InternalError as e:
            rank_cron_log(f"LEGACY: ERROR: Can't update player mmr of: {player_id}, skipping")
            id += 1
            await asyncio.sleep(2.5)
            continue
        rank_cron_log(f"LEGACY: Updated rank for: {player_id}")
            
        # rank cron
        
        rank_cron_log(f"LEGACY: Updating rank for: {player_id}")
        mmr = await get_mmr(player_id)
        if mmr == 0:
            rank = RankMMR.UNRANKED
        else:
            ranks = [x.value for x in RankMMR.__members__.values() if not x.value is None] # closest rank
            abs_diff = lambda value: abs(value-mmr)
            rank = RankMMR(min(ranks, key=abs_diff)) # find rank that catergorizes player best and convert to enum
        try:
            await sql.execute("UPDATE `players` SET `rank` = %s WHERE `player_id` = %s;", (rank.name.lower(), player_id))
        except pymysql.InternalError as e:
            rank_cron_log(f"LEGACY: ERROR: Can't set final rank: {rank.name.lower()} of player: {player_id}, skipping")
            id += 1
            await asyncio.sleep(2.5)
            continue
        rank_cron_log(f"LEGACY: Updated rank for: {player_id}, {rank.name.lower()}")
        id += 1
        await asyncio.sleep(2.5)

async def player_cron():
    global LAST_CRON_LOG
    client = laserforce.Client()

    for i in range(10000):
        player_cron_log(f"Attemping to database player: 4-43-{i}")
        try:
            player = client.get_player(f"4-43-{i}")
        except LookupError: # player does not exist
            player_cron_log(f"Player: 4-43-{i} does not exist, skipping")
            continue
        
        try:
            await database_player(f"4-43-{i}", player.codename)
        except pymysql.InternalError:
            continue
        player_cron_log(f"Databased player: 4-43-{i}, {player.codename}")

async def fetch_player(id: int) -> Player:
    q = await sql.fetchall("SELECT * FROM `players` WHERE `id` = %s", (id))
    return Player(*q[0])

async def get_player(player_id: str) -> Player:
    q = await sql.fetchall("SELECT * FROM `players` WHERE `player_id` = %s", (player_id))
    return Player(*q[0])

async def fetch_player_by_name(codename: int) -> Player:
    q = await sql.fetchall("SELECT * FROM `players` WHERE `codename` = %s", (codename))
    return Player(*q[0])

async def database_player(player_id: str, codename: str) -> None:
    client = laserforce.Client()
    ipl_id = client.get_player(player_id).ipl_id
    
    if await sql.fetchone("SELECT id FROM `players` WHERE `player_id` = %s", (player_id)): # update stuff.
        await sql.execute("""UPDATE `players` SET `codename` = %s WHERE `player_id` = %s""", (codename, player_id))

        await sql.execute("""UPDATE `players` SET `ipl_id` = %s WHERE `player_id` = %s""", (ipl_id, player_id))
    else:
        try:
            await sql.execute("""INSERT IGNORE INTO `players` (player_id, ipl_id, codename, rank, ranking_scout, ranking_heavy, ranking_medic, ranking_ammo, ranking_commander)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", (player_id, ipl_id, codename, "unranked", 0.0, 0.0, 0.0, 0.0, 0.0))
        except pymysql.ProgrammingError:
            pass

async def log_game(game: Game) -> None:
    last_row = await sql.fetchone("""INSERT INTO `games` (winner)
                        VALUES (%s);SELECT LAST_INSERT_ID();""", (game.winner))
    
    # update elo
    
    k = 512 # k-factor of elo
    
    if game.winner == Team.RED:
        winner_int = 0
    else: # is green
        winner_int = 1
        
    game.red, game.green = update_elo(game.red, game.green, winner_int, k) # update elo
    game.players = [*game.red, *game.green]
    
    for player in game.players:
        player.game_id = last_row
        
        await sql.execute("""INSERT INTO `game_players` (player_id, game_id, team, role, score)
                            VALUES (%s, %s, %s, %s, %s)""", (player.player_id, player.game_player.game_id, player.game_player.team.value, player.game_player.role.value, player.game_player.score))
        
        await sql.execute("UPDATE `players` SET `elo` = %s WHERE `player_id` = %s", (player.elo, player.player_id))
    
async def fetch_game_players(game_id: int) -> List[GamePlayer]:
    q = await sql.fetchall("SELECT * FROM `game_players` WHERE `game_id` = %s", (game_id))
    final = []

    for game_player in q:
        nplayer = []

        nplayer.append(game_player[0])
        nplayer.append(game_player[1])
        nplayer.append(Team(game_player[2]))
        nplayer.append(Role(game_player[3]))
        nplayer.append(game_player[4])
        
        player = await get_player(game_player[0])
        player.game_player = GamePlayer(*nplayer)
        
        final.append(player)
    return final

async def fetch_game_players_team(game_id: int, team: Team) -> List[GamePlayer]:
    q = await sql.fetchall("SELECT * FROM `game_players` WHERE `game_id` = %s AND `team` = %s", (game_id, team.value))
    final = []
    
    for game_player in q:
        nplayer = []

        nplayer.append(game_player[0])
        nplayer.append(game_player[1])
        nplayer.append(Team(game_player[2]))
        nplayer.append(Role(game_player[3]))
        nplayer.append(game_player[4])
        
        player = await get_player(game_player[0])
        player.game_player = GamePlayer(*nplayer)
        
        final.append(player)
    return final
    
async def fetch_game(id: int) -> Game:
    q = await sql.fetchall("SELECT * FROM `games` WHERE `id` = %s", (id))
    game = Game(*q[0])
    players = await fetch_game_players(game.id)
    green = await fetch_game_players_team(game.id, Team.GREEN)
    red = await fetch_game_players_team(game.id, Team.RED)
    game.players = players
    game.green = green
    game.red = red
    return game

def remove_values_from_list(the_list, val):
   return [value for value in the_list if value != val]

#async def get_my_ranking_score(role: Role, player_id: str):
#    q = await sql.fetchall("SELECT `score` FROM `game_players` WHERE `role` = %s AND `player_id` = %s", (role.value, player_id))
#    games = format_sql(q)[:10] # grab top 10 games
#    weighted = 0
#    for i, score in enumerate(games): # use weighting algrorthim
#        weighted += int(score * 0.95**i)
#    return weighted # only top 10 weighted

async def get_average_score(role: Role, player_id: str) -> int: # the world (everyone else's)
    q = await sql.fetchall(f"SELECT `score` FROM `game_players` WHERE `role` = %s AND NOT `player_id` = %s", (role.value, player_id))
    q = remove_values_from_list(format_sql(q), 0)
    try:
        ret = average(q)
    except ZeroDivisionError:
        ret = 0
    return ret

async def get_my_average_score(role: Role, player_id: str): # my average score
    q = await sql.fetchall(f"SELECT `score` FROM `game_players` WHERE `role` = %s AND `player_id` = %s", (role.value, player_id))
    q = remove_values_from_list(format_sql(q), 0)
    try:
        ret = average(q)
    except ZeroDivisionError:
        ret = 0
    return ret
    
async def get_my_ranking_score(role: Role, player_id: str) -> float:
    world_average = await get_average_score(role, player_id)
    my_average = await get_my_average_score(role, player_id)
    try:
        ret = round(my_average / world_average, 2)
    except ZeroDivisionError:
        ret = 0
    return ret

async def init_sql():
    global sql
    if not sql:
        sql = await mysql.MySQLPool.connect(config["db_host"], config["db_user"],
                                config["db_password"], config["db_database"],
                                config["db_port"])