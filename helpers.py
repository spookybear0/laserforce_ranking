import logging
from types import CodeType
import mysql # type: ignore
from typing import List, Union, Tuple
from config import config # type: ignore
from objects import Player, Game, Role, RankMMR, Rank, GamePlayer, Team # type: ignore
import laserforce # type: ignore
import pymysql
import asyncio
from elo import get_win_chance, update_elo

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
    all_mmr = list(q[0])
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
    q = format_sql(q)
    return len(q)

async def recalculate_elo():
    elo_logger.info("Recalculating elo")
    base_elo = 1200
    
    # reset elo
    elo_logger.debug(f"Resetting base elo ({base_elo})")
    await sql.execute("UPDATE `players` SET `elo` = %s", (base_elo,))
    elo_logger.debug(f"Reset to {base_elo}")
    
    in_a_row = 0
    i = 1
    while True:
        try:
            elo_logger.debug(f"Fetching game with id {i}")
            game = await fetch_game(i)
        except IndexError:
            in_a_row += 1
            if in_a_row >= 100:
                break
            i += 1
            continue
        elo_logger.debug(f"Fetched game with id {i}")
        
        in_a_row = 0
        
        k = 512
        
        if game.winner == Team.RED:
            winner_int = 0
        else: # is green
            winner_int = 1
        
        elo_logger.debug(f"Updating elo for game id {i}")
        game.red, game.green = await update_elo(game.red, game.green, winner_int, k) # update elo
        game.players = [*game.red, *game.green]
        elo_logger.debug(f"Done updating for game id {i}")
        
        elo_logger.debug(f"Setting all players elo to updated value for game id {i}")
        for player in game.players:
            player.game_id = game.id
        
            await sql.execute("UPDATE `players` SET `elo` = %s WHERE `player_id` = %s", (player.elo, player.player_id))
        
        i += 1
    elo_logger.info("Done recalculating elo")
        
# deprecated
async def legacy_ranking_cron():
    logger.debug(f"LEGACY: Starting to update rankings")
    roles = list(Role)
    id = 1
    while True:
        logger.debug(f"LEGACY: Searching for player at index {id}")
        try:
            player_id = await sql.fetchone("SELECT player_id FROM `players` WHERE `id` = %s", id)
        except:
            break
        try:
            player_id = player_id[0]
        except TypeError:
            break
        # mmr cron
        logger.debug(f"LEGACY: Updating rank for: {player_id}")
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
            logger.exception(f"LEGACY: Can't update player mmr of: {player_id}, skipping")
            id += 1
            continue
        logger.debug(f"LEGACY: Updated rank for: {player_id}")
            
        # rank cron
        
        logger.debug(f"LEGACY: Updating rank for: {player_id}")
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
            logger.exception(f"LEGACY: Can't set final rank: {rank.name.lower()} of player: {player_id}, skipping")
            id += 1
            continue
        logger.debug(f"LEGACY: Updated rank for: {player_id}, {rank.name.lower()}")
        id += 1
        await asyncio.sleep(2.5)

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
            await sql.execute("""INSERT IGNORE INTO `players` (player_id, ipl_id, codename, rank, ranking_scout, ranking_heavy, ranking_medic, ranking_ammo, ranking_commander)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", (player_id, ipl_id, codename, "unranked", 0.0, 0.0, 0.0, 0.0, 0.0))
        except pymysql.ProgrammingError:
            pass

async def log_game(game: Game) -> None:
    elo_logger.info("Inserting game")
    await sql.execute("""INSERT INTO `games` (winner)
                        VALUES (%s);""", (game.winner))
    elo_logger.debug("Inserted game")
    
    last_row = await sql.fetchone("SELECT LAST_INSERT_ID();")
    last_row = last_row[0]
    
    # update elo
    
    k = 512 # k-factor of elo
    
    if game.winner == Team.RED:
        winner_int = 0
    else: # is green
        winner_int = 1
    
    elo_logger.debug("Updating players elo for game")
    game.red, game.green = await update_elo(game.red, game.green, winner_int, k) # update elo
    game.players = [*game.red, *game.green]
    elo_logger.debug("Done updating elo")
    
    elo_logger.debug("Setting elo in mysql")
    for player in game.players:
        player.game_player.game_id = last_row
        
        await sql.execute("""INSERT INTO `game_players` (player_id, game_id, team, role, score)
                            VALUES (%s, %s, %s, %s, %s)""", (player.player_id, player.game_player.game_id, player.game_player.team.value, player.game_player.role.value, player.game_player.score))
        
        await sql.execute("UPDATE `players` SET `elo` = %s WHERE `player_id` = %s", (player.elo, player.player_id))
    elo_logger.info("Done logging game")
    
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
    green = await fetch_game_players_team(game.id, Team.GREEN)
    red = await fetch_game_players_team(game.id, Team.RED)
    game.players = [*green, *red]
    game.green = green
    game.red = red
    return game

def remove_values_from_list(the_list, val):
   return [value for value in the_list if value != val]

# deprecated
#async def get_my_ranking_score(role: Role, player_id: str):
#    q = await sql.fetchall("SELECT `score` FROM `game_players` WHERE `role` = %s AND `player_id` = %s", (role.value, player_id))
#    games = format_sql(q)[:10] # grab top 10 games
#    weighted = 0
#    for i, score in enumerate(games): # use weighting algrorthim
#        weighted += int(score * 0.95**i)
#    return weighted # only top 10 weighted

async def get_average_score(role: Role, player_id: str=None) -> int: # the world
    if player_id:
        q = await sql.fetchall(f"SELECT `score` FROM `game_players` WHERE `role` = %s AND NOT `player_id` = %s", (role.value, player_id))
    else:
        q = await sql.fetchall(f"SELECT `score` FROM `game_players` WHERE `role` = %s", (role.value))
    q = remove_values_from_list(format_sql(q), 0)
    try:
        ret = average(q)
    except ZeroDivisionError:
        ret = 0
    return ret

# deprecated
async def get_my_average_score(role: Role, player_id: str): # my average score
    q = await sql.fetchall(f"SELECT `score` FROM `game_players` WHERE `role` = %s AND `player_id` = %s", (role.value, player_id))
    q = remove_values_from_list(format_sql(q), 0)
    try:
        ret = average(q)
    except ZeroDivisionError:
        ret = 0
    return ret

# deprecated
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