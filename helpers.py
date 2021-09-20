import mysql # type: ignore
from typing import List, Union, Tuple
from config import config # type: ignore
from objects import Player, Game, Role # type: ignore
import laserforce # type: ignore

sql = None

def average(to_average: Union[List, Tuple]):
    return sum(to_average) / len(to_average)

def format_sql(to_format):
    final = []
    for i in to_format:
        final.append(i[0])
    return final

async def get_top_100(role: Role, amount: int=100):
    q = await sql.fetchall(f"SELECT codename, player_id FROM players ORDER BY ranking_{role.value} DESC LIMIT {amount}")
    return list(q)

async def get_all_players():
    q = await sql.fetchall("SELECT player_id FROM players")
    return format_sql(q)
    
async def ranking_cron():
    roles = list(Role)
    for player_id in await get_all_players():
        for role in roles:
            try:
                score = await get_my_ranking_score(role, player_id)
            except ZeroDivisionError: # no games
                score = 0
            await sql.execute(f"UPDATE players SET ranking_{role.value} = %s WHERE player_id = %s", (score, player_id))
            
async def player_cron():
    client = laserforce.Client()

    for i in range(5000):
        try:
            player = client.get_player(f"4-43-{i}")
        except LookupError: # player does not exist
            continue
        
        await database_player(f"4-43-{i}", player.codename)

async def fetch_player(id: int) -> Game:
    q = await sql.fetchall("SELECT * FROM `players` WHERE `id` = %s", (id))
    return Player(*q[0])

async def fetch_player_by_name(codename: int) -> Game:
    q = await sql.fetchall("SELECT * FROM `players` WHERE `codename` = %s", (codename))
    return Player(*q[0])

async def database_player(player_id: str, codename: str) -> None:
    # clean codename
    
    if await sql.fetchone("SELECT id FROM `players` WHERE player_id = %s", (player_id)):
        await sql.execute("""UPDATE `players` (player_id, codename, ranking_scout, ranking_heavy, ranking_medic, ranking_ammo, ranking_commander)
                            SET player_id = %s, codename = %s WHERE player_id = %s""", (player_id, codename, player_id))
    elif await sql.fetchone("SELECT id FROM `players` WHERE codename = %s", (codename)):
        await sql.execute("""UPDATE `players` (player_id, codename, ranking_scout, ranking_heavy, ranking_medic, ranking_ammo, ranking_commander)
                            SET player_id = %s, codename = %s WHERE codename = %s""", (player_id, codename, codename))
    else:
        await sql.execute("""INSERT INTO `players` (player_id, codename, ranking_scout, ranking_heavy, ranking_medic, ranking_ammo, ranking_commander)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)""", (player_id, codename, 0.0, 0.0, 0.0, 0.0, 0.0))
        

async def log_game(player_id: str, won: bool, role: str, score: int) -> None:
    await sql.execute("""INSERT INTO `games` (player_id, won, role, score)
                        VALUES (%s, %s, %s, %s)""", (player_id, int(won), role.value, score))
    
async def fetch_game(id: int) -> Game:
    q = await sql.fetchall("SELECT * FROM `games` WHERE `id` = %s", (id))
    return Game(*q[0])

async def get_my_ranking_score(role: Role, player_id: str):
    q = await sql.fetchall("SELECT `score` FROM `games` WHERE `role` = %s AND `player_id` = %s", (role.value, player_id))
    games = format_sql(q)[:10]
    weighted = 0
    for i, score in enumerate(games):
        weighted += int(score * 0.95**i)
    return weighted # only top 10 weighted

async def init_sql():
    global sql
    if not sql:
        sql = await mysql.MySQLPool.connect(config["db_host"], config["db_user"],
                                config["db_password"], config["db_database"],
                                config["db_port"])