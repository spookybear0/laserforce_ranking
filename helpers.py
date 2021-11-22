from types import CodeType
import mysql # type: ignore
from typing import List, Union, Tuple
from config import config # type: ignore
from objects import Player, Game, Role, RankMMR, Rank, GamePlayer, Team # type: ignore
from glob import player_cron_log, rank_cron_log # type: ignore
import laserforce # type: ignore
import pymysql
import asyncio

sql = None

def average(to_average: Union[List, Tuple]):
    return sum(to_average) / len(to_average)

# iron: 0.75, 75%
# bronze: 0.85, 85%
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
    all_mmr = format_sql(q) # format
    if all_mmr == []:
        return 0
    mmr = average(all_mmr)
    return mmr

async def get_games_played(player_id: str):
    q = await sql.fetchall("SELECT * FROM `game_players` WHERE `player_id` = %s", (player_id))
    q = format_sql(q) # format
    return len(q)
    
async def ranking_cron():
    roles = list(Role)
    id = 0
    while True:
        rank_cron_log(f"Searching for player at index {id}")
        try:
            player_id = await sql.fetchone("SELECT player_id FROM `players` WHERE `id` = %s", id)
        except pymysql.InternalError as e:
            rank_cron_log(f"ERROR: Player at index {id} doesn't exist, skipping")
            continue
        try:
            player_id = player_id[0]
        except TypeError:
            continue
        # mmr cron
        rank_cron_log(f"Updating rank for: {player_id}")
        for role in roles:
            try:
                score = await get_my_ranking_score(role, player_id)
            except ZeroDivisionError: # no games
                score = 0
            try:
                await sql.execute(f"UPDATE players SET ranking_{role.value} = %s WHERE player_id = %s", (score, player_id))
            except pymysql.InternalError as e:
                rank_cron_log(f"ERROR: Can't update role: {role.value} of player: {player_id}, skipping")
                continue
        rank_cron_log(f"Updated rank for: {player_id}")
            
        # rank cron
        
        rank_cron_log(f"Updating rank for: {player_id}")
        mmr = await get_mmr(player_id)
        if mmr == 0:
            rank = RankMMR.UNRANKED
        else:
            ranks = [x.value for x in RankMMR.__members__.values() if not x.value is None]
            abs_diff = lambda value: abs(value-mmr)
            rank = RankMMR(min(ranks, key=abs_diff)) # find rank that catergorizes player best and convert to enum
        rank_cron_log(f"Updated rank for: {player_id}, {rank.name.lower()}")
        try:
            await sql.execute("UPDATE `players` SET `rank` = %s WHERE `player_id` = %s;", (rank.name.lower(), player_id))
        except pymysql.InternalError as e:
            rank_cron_log(f"ERROR: Can't set final rank: {rank.name.lower()} of player: {player_id}, skipping")
            continue
        id += 1

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
        
        await database_player(f"4-43-{i}", player.codename)
        player_cron_log(f"Databased player: 4-43-{i}, {player.codename}")
        await asyncio.sleep(0.5)

async def fetch_player(id: int) -> Player:
    q = await sql.fetchall("SELECT * FROM `players` WHERE `id` = %s", (id))
    return Player(*q[0])

async def get_player(player_id: str) -> Player:
    q = await sql.fetchall("SELECT * FROM `players` WHERE `player_id` = %s", (player_id))
    return Player(*q[0])

async def fetch_player_by_name(codename: int) -> Game:
    q = await sql.fetchall("SELECT * FROM `players` WHERE `codename` = %s", (codename))
    return Player(*q[0])

async def database_player(player_id: str, codename: str) -> None:
    client = laserforce.Client()
    ipl_id = client.get_player(player_id).ipl_id
    
    if await sql.fetchone("SELECT id FROM `players` WHERE `player_id` = %s", (player_id)): # update stuff.
        await sql.execute("""UPDATE `players` SET `codename` = %s WHERE `player_id` = %s""", (codename, player_id))

        await sql.execute("""UPDATE `players` SET `ipl_id` = %s WHERE `player_id` = %s""", (ipl_id, player_id))
    else:
        await sql.execute("""INSERT INTO `players` (player_id, ipl_id, codename, rank, ranking_scout, ranking_heavy, ranking_medic, ranking_ammo, ranking_commander)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", (player_id, ipl_id, codename, "unranked", 0.0, 0.0, 0.0, 0.0, 0.0))

async def log_game(game: Game) -> None:
    await sql.execute("""INSERT INTO `games` (winner)
                        VALUES (%s)""", (game.winner))
    last_row = sql.last_row_id
    for player in game.players:
        player.game_id = last_row
        await sql.execute("""INSERT INTO `game_players` (player_id, game_id, team, role, score)
                            VALUES (%s, %s, %s, %s, %s)""", (player.player_id, player.game_id, player.team.value, player.role.value, player.score))
    
async def fetch_game_players(game_id: int) -> List[GamePlayer]:
    q = await sql.fetchall("SELECT * FROM `game_players` WHERE `game_id` = %s", (game_id))
    final = []
    for player in q:
        player[2] = Team(player[2])
        player[3] = Role(player[3])
        final.append(GamePlayer(*player))
    return final
    
async def fetch_game(id: int) -> Game:
    q = await sql.fetchall("SELECT * FROM `games` WHERE `id` = %s", (id))
    game = Game(*q[0])
    players = await fetch_game_players(game.id)
    game.players = players
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
        ret = round(world_average / my_average, 2)
    except ZeroDivisionError:
        ret = 0
    return ret

async def init_sql():
    global sql
    if not sql:
        sql = await mysql.MySQLPool.connect(config["db_host"], config["db_user"],
                                config["db_password"], config["db_database"],
                                config["db_port"])