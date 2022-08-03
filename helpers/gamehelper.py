from shared import sql
from objects import Game, GameType, Team
from helpers import ratinghelper
from typing import List
import asyncio

def avg(iter: List):
    return sum(iter) / len(iter)

async def get_total_games_played():
    q = await sql.fetchone("SELECT COUNT(*) FROM sm5_game_players")
    q2 = await sql.fetchone("SELECT COUNT(*) FROM laserball_game_players")
    return q[0] + q2[0]

async def get_total_games():
    q = await sql.fetchone("SELECT COUNT(*) FROM games")
    return q[0]

async def log_sm5_game(game: Game):
    await sql.execute("INSERT INTO `games` (winner, type) VALUES (%s, %s);", (game.winner.value, game.type.value))
    
    # gets id of the inserted game
    last_row = await sql.fetchone("SELECT LAST_INSERT_ID();")
    game_id = last_row[0]
    
    game.red, game.green = await ratinghelper.update_elo(game, GameType.SM5)
    game.players = [*game.red, *game.green]

    # update openskill
    
    for player in game.players:
        player.game_player.game_id = game_id

        await sql.execute(
            """INSERT INTO `sm5_game_players` (player_id, game_id, team, role, score)
                            VALUES (%s, %s, %s, %s, %s)""",
            (
                player.player_id,
                player.game_player.game_id,
                player.game_player.team.value,
                player.game_player.role.value,
                player.game_player.score,
            ),
        )

        # update rating
        await sql.execute("""
            UPDATE players SET
            sm5_mu = %s,
            sm5_sigma = %s
            WHERE id = %s
        """, (
            player.sm5_mu, player.sm5_sigma,
            player.id
        ))
        
async def log_laserball_game(game: Game):
    await sql.execute("INSERT INTO `games` (winner, type) VALUES (%s, %s);", (game.winner.value, game.type.value))
    
    # gets id of the inserted game
    last_row = await sql.fetchone("SELECT LAST_INSERT_ID();")
    game_id = last_row[0]
    
    game.red, game.blue = await ratinghelper.update_elo(game, GameType.LASERBALL)
    game.players = [*game.red, *game.blue]

    # update openskill
    
    for player in game.players:
        player.game_player.game_id = game_id

        await sql.execute(
            """INSERT INTO `laserball_game_players` (player_id, game_id, team, goals, assists, steals, clears, blocks)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                player.player_id,
                player.game_player.game_id,
                player.game_player.team.value,
                player.game_player.goals,
                player.game_player.assists,
                player.game_player.steals,
                player.game_player.clears,
                player.game_player.blocks,
            ),
        )

        # update rating
        await sql.execute("""
            UPDATE players SET
            laserball_mu = %s,
            laserball_sigma = %s
            WHERE id = %s
        """, (
            player.laserball_mu, player.laserball_sigma,
            player.id
        ))

async def get_all_games() -> List[Game]:
    games = []
    game_count = await get_total_games()

    for i in range(1, game_count + 50):
        game: Game = await Game.from_id(i)
        if game:
            games.append(game)
    return games

async def reset_ratings() -> None:
    await sql.execute("UPDATE players SET sm5_mu = %s, sm5_sigma = %s, laserball_mu = %s, laserball_sigma = %s", (25, 25/3, 25, 25/3))

async def relog_all_games() -> None:
    """
    if this fails i will need to manually add the games to the database
    so
    i really
    hope
    that it
    doesn't
    fail

    PLEASd-= basokup the datasbase beorer rundniong thsi fgfcommandsd
    """
    print("Getting all games...")

    await reset_ratings()

    games: List[Game] = await get_all_games()

    # > TRUNCATE THE TABLES
    # >>> BUT SIR
    # > JUST DO IT
    print("Truncating tables")
    await sql.execute("TRUNCATE TABLE games;")
    await sql.execute("TRUNCATE TABLE sm5_game_players;")
    await sql.execute("TRUNCATE TABLE laserball_game_players;")

    for game in games:
        print(f"Logging game {game.id} of type {game.type.value}")
        await game._reload_elo()
        if game.type == GameType.SM5:
            await log_sm5_game(game)
        elif game.type == GameType.LASERBALL:
            await log_laserball_game(game)

async def get_wins(game_type: GameType, team: Team) -> int:
    wins = await sql.fetchone("SELECT COUNT(*) FROM games WHERE winner = %s AND type = %s;", (team.value, game_type.value))
    return wins[0]

async def get_teams(game_type: GameType, team: Team, player_id: str) -> int:
    wins = await sql.fetchone(f"SELECT COUNT(*) FROM {game_type.value}_game_players WHERE team = %s AND player_id = %s;", (team.value, player_id))
    return wins[0]

# i think this works
async def get_win_percent(game_type: GameType, player_id: str) -> float:
    wins = await sql.fetchone(f"""SELECT AVG(CASE WHEN games.winner = {game_type.value}_game_players.team THEN 1 ELSE 0 END)
                                FROM games
                                INNER JOIN {game_type.value}_game_players
                                ON games.id = {game_type.value}_game_players.game_id
                                WHERE {game_type.value}_game_players.player_id = %s;""",
                            (player_id,))
    if not wins[0]:
        return 0.0
    return round(float(wins[0]), 2)


async def get_win_percent_overall(player_id: str) -> float:
    wins_1 = await sql.fetchall(f"""SELECT CASE WHEN games.winner = sm5_game_players.team THEN 1 ELSE 0 END
                                FROM games
                                INNER JOIN sm5_game_players
                                ON games.id = sm5_game_players.game_id
                                WHERE sm5_game_players.player_id = %s;""",
                            (player_id,))

    wins_2 = await sql.fetchall(f"""SELECT CASE WHEN games.winner = laserball_game_players.team THEN 1 ELSE 0 END
                                FROM games
                                INNER JOIN laserball_game_players
                                ON games.id = laserball_game_players.game_id
                                WHERE laserball_game_players.player_id = %s;""",
                            (player_id,))
    
    wins = []

    for i in [*wins_1, *wins_2]:
        wins.append(i[0])

    return round(float(avg(wins)), 2)