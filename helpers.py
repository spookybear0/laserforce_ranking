import logging
from types import CodeType
import mysql # type: ignore
from typing import List, Union, Tuple
from config import config # type: ignore
from objects import Player, SM5_Game, Role, RankMMR, Rank, SM5GamePlayer, LaserballGamePlayer, Team, Laserball_Game # type: ignore
import laserforce # type: ignore
import pymysql
import asyncio
from parse_tdf import parse_sm5_game, SM5_TDF_Game
import os

logger = logging.getLogger("general")
elo_logger = logging.getLogger("elo cron")
player_logger = logging.getLogger("player cron")

sql = None

def average(to_average: Union[List, Tuple]):
    return sum(to_average) / len(to_average)

# deprecated
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

# rfid
def to_hex(tag: str):
    return "LF/0D00" + hex(int(tag)).strip("0x").upper()

def to_decimal(tag: str):
    return "000" + str(int(tag.strip("LF/").strip("0D00"), 16))

def calculate_laserball_mvp_points(player: LaserballGamePlayer):
    mvp_points = 0
    
    mvp_points += player.goals * 1
    mvp_points += player.assists * 0.75
    mvp_points += player.steals * 0.5
    mvp_points += player.clears * 0.25 # clear implies a steal so the total gained is 0.75
    mvp_points += player.blocks * 0.3
    
    return mvp_points

async def get_top_100(amount: int=100, start: int=0):
    q = await sql.fetchall(f"SELECT codename, player_id FROM players ORDER BY LENGTH(player_id), player_id ASC LIMIT {amount} OFFSET {start}")
    return list(q)

async def get_total_players():
    q = await sql.fetchone("SELECT COUNT(*) FROM players")
    return q[0]

async def get_total_games():
    q = await sql.fetchone("SELECT COUNT(*) FROM sm5_games")
    q2 = await sql.fetchone("SELECT COUNT(*) FROM laserball_games")
    return q[0] + q2[0]

async def get_total_games_played():
    q = await sql.fetchone("SELECT COUNT(*) FROM sm5_game_players")
    q2 = await sql.fetchone("SELECT COUNT(*) FROM laserball_game_players")  
    return q[0] + q2[0]

async def get_games_played(player_id: str):
    q = await sql.fetchone("SELECT COUNT(*) FROM `sm5_game_players` WHERE `player_id` = %s", (player_id))
    q2 = await sql.fetchone("SELECT COUNT(*) FROM `laserball_game_players` WHERE `player_id` = %s", (player_id))
    return q[0] + q2[0]

async def player_cron():
    global LAST_CRON_LOG
    client = laserforce.Client()

    for i in range(10000):
        player_logger.debug(f"Attemping to database player: 4-43-{i}")
        try:
            player = client.get_player(f"4-43-{i}")
        except LookupError: # player does not exist
            player_logger.warning(f"Player: 4-43-{i} does not exist, skipping")
            continue
        
        try:
            await database_player(f"4-43-{i}", player.codename)
        except pymysql.InternalError:
            player_logger.exception(f"Unable to database 4-43-{i}, {player.codename}")
            continue
        player_logger.debug(f"Databased player: 4-43-{i}, {player.codename}")

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
            await sql.execute("""INSERT IGNORE INTO `players` (player_id, ipl_id, codename)
                                VALUES (%s, %s, %s)""", (player_id, ipl_id, codename))
        except pymysql.ProgrammingError:
            pass

async def log_sm5_game(game: SM5_Game) -> None:
    elo_logger.info("Inserting game")
    await sql.execute("""INSERT INTO `sm5_games` (winner)
                        VALUES (%s);""", (game.winner))
    elo_logger.debug("Inserted game")
    
    last_row = await sql.fetchone("SELECT LAST_INSERT_ID();")
    last_row = last_row[0]
    
    if game.winner == Team.RED:
        winner_int = 0
    else: # is green
        winner_int = 1
        
    # update elo
    
    # update openskill
    
    elo_logger.debug("Setting elo in mysql")
    for player in game.players:
        player.game_player.game_id = last_row
        
        await sql.execute("""INSERT INTO `sm5_game_players` (player_id, game_id, team, role, score)
                            VALUES (%s, %s, %s, %s, %s)""", (player.player_id, player.game_player.game_id, player.game_player.team.value, player.game_player.role.value, player.game_player.score))
        
    elo_logger.info("Done logging game")
    
async def fetch_game_players(game_id: int, type="sm5") -> List[SM5GamePlayer]:
    q = await sql.fetchall(f"SELECT * FROM `{type}_game_players` WHERE `game_id` = %s", (game_id))
    final = []

    for game_player in q:
        nplayer = []

        nplayer.append(game_player[0])
        nplayer.append(game_player[1])
        nplayer.append(Team(game_player[2]))
        nplayer.append(Role(game_player[3]))
        nplayer.append(game_player[4])
        
        player = await get_player(game_player[0])
        if type == "sm5":
            player.game_player = SM5GamePlayer(*nplayer)
        else:
            player.game_player = LaserballGamePlayer(*nplayer)
        
        final.append(player)
    return final

async def fetch_game_players_team(game_id: int, team: Team, type="sm5") -> List[SM5GamePlayer]:
    q = await sql.fetchall(f"SELECT * FROM `{type}_game_players` WHERE `game_id` = %s AND `team` = %s", (game_id, team.value))
    final = []
    
    if type == "sm5":
        for game_player in q:
            nplayer = []

            nplayer.append(game_player[0])
            nplayer.append(game_player[1])
            nplayer.append(Team(game_player[2]))
            nplayer.append(Role(game_player[3]))
            nplayer.append(game_player[4])
            
            player = await get_player(game_player[0])
            
            player.game_player = SM5GamePlayer(*nplayer)
            
            final.append(player)
    elif type == "laserball":
        for game_player in q:
            nplayer.append(game_player[0])
            nplayer.append(game_player[1])
            nplayer.append(Team(game_player[2]))
            nplayer.append(game_player[3])
            nplayer.append(game_player[4])
            nplayer.append(game_player[5])
            nplayer.append(game_player[6])
            nplayer.append(game_player[7])
            
            player = await get_player(game_player[0])
            
            player.game_player = LaserballGamePlayer(*nplayer)
            final.append(player)
    return final
    
async def fetch_sm5_game(id: int) -> SM5_Game:
    q = await sql.fetchall("SELECT * FROM `sm5_games` WHERE `id` = %s", (id))
    game = SM5_Game(*q[0])
    green = await fetch_game_players_team(game.id, Team.GREEN, "sm5")
    red = await fetch_game_players_team(game.id, Team.RED, "sm5")
    game.players = [*green, *red]
    game.green = green
    game.red = red
    return game

async def fetch_laserball_game(id: int) -> Laserball_Game:
    q = await sql.fetchall("SELECT * FROM `laserball_games` WHERE `id` = %s", (id))
    game = Laserball_Game(*q[0])
    blue = await fetch_game_players_team(game.id, Team.BLUE, "laserball")
    red = await fetch_game_players_team(game.id, Team.RED, "laserball")
    game.players = [*blue, *red]
    game.blue = blue
    game.red = red
    return game

def remove_values_from_list(the_list, val):
   return [value for value in the_list if value != val]

async def init_sql():
    global sql
    if not sql:
        sql = await mysql.MySQLPool.connect(config["db_host"], config["db_user"],
                                config["db_password"], config["db_database"],
                                config["db_port"])