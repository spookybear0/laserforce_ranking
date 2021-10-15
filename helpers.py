import mysql # type: ignore
from typing import List, Union, Tuple
from config import config # type: ignore
from objects import Player, Game, Role, RankMMR, Rank, GamePlayer, Team # type: ignore
import laserforce # type: ignore

sql = None

def average(to_average: Union[List, Tuple]):
    return sum(to_average) / len(to_average)

# iron: 0.75, 75%
# bronze: 0.85, 85%
# silver: 1.0, 100% (average)
# gold: 1.15, 115%
# diamond: 1.25, 125%
# immortal: 1.35, 135%
# lasermaster: top 500 average mmr

def format_sql(to_format) -> List:
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

async def get_mmr(player_id: str):
    q = await sql.fetchall("SELECT ranking_scout, ranking_heavy, ranking_commander, ranking_medic, ranking_ammo FROM `players` WHERE `player_id` = %s", (player_id))
    all_mmr = format_sql(q) # format
    mmr = average(all_mmr)
    return mmr

async def get_games_played(player_id: str):
    q = await sql.fetchall("SELECT * FROM `game_players` WHERE `player_id` = %s", (player_id))
    q = format_sql(q) # format
    return len(q)
    
async def ranking_cron():
    roles = list(Role)
    for player_id in await get_all_players():
        # mmr cron
        for role in roles:
            try:
                score = await get_my_ranking_score(role, player_id)
            except ZeroDivisionError: # no games
                score = 0
            await sql.execute(f"UPDATE players SET ranking_{role.value} = %s WHERE player_id = %s", (score, player_id))
            
        # rank cron
        
        mmr = await get_mmr(player_id)
        ranks = [x.value for x in RankMMR.__members__.values() if not x.value is None]
        abs_diff = lambda value: abs(value-mmr)
        rank = RankMMR(min(ranks, key=abs_diff)) # find rank that catergorizes player best and convert to enum
        await sql.execute("""UPDATE players SET rank = %s WHERE player_id = %s""", (rank.name.lower(), player_id))

async def player_cron():
    client = laserforce.Client()

    for i in range(10000):
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
    if await sql.fetchone("SELECT id FROM `players` WHERE player_id = %s", (player_id)):
        await sql.execute("""UPDATE `players` SET player_id = %s, codename = %s WHERE player_id = %s""", (player_id, codename, player_id))
    elif await sql.fetchone("SELECT id FROM `players` WHERE codename = %s", (codename)):
        await sql.execute("""UPDATE `players` SET player_id = %s, codename = %s WHERE codename = %s""", (player_id, codename, codename))
    else:
        await sql.execute("""INSERT INTO `players` (player_id, codename, rank, ranking_scout, ranking_heavy, ranking_medic, ranking_ammo, ranking_commander)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""", (player_id, codename, "unranked", 0.0, 0.0, 0.0, 0.0, 0.0))

async def log_game(game: Game) -> None:
    await sql.execute("""INSERT INTO `games` (winner)
                        VALUES (%s)""", (int(game.winner)))
    for player in game.players:
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

async def get_my_ranking_score(role: Role, player_id: str):
    q = await sql.fetchall("SELECT `score` FROM `game_players` WHERE `role` = %s AND `player_id` = %s", (role.value, player_id))
    games = format_sql(q)[:10] # grab top 10 games
    weighted = 0
    for i, score in enumerate(games): # use weighting algrorthim
        weighted += int(score * 0.95**i)
    return weighted # only top 10 weighted

async def init_sql():
    global sql
    if not sql:
        sql = await mysql.MySQLPool.connect(config["db_host"], config["db_user"],
                                config["db_password"], config["db_database"],
                                config["db_port"])