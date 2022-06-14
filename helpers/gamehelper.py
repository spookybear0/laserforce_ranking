from shared import sql
from objects import Game, GameType
from helpers import ratinghelper

async def log_sm5_game(game: Game):
    await sql.execute("INSERT INTO `games` (winner, type) VALUES (%s, %s);", (game.winner, game.type.value))
    
    # gets id of the inserted game
    last_row = await sql.fetchone("SELECT LAST_INSERT_ID();")
    game_id = last_row[0]
    
    game.red, game.green = await ratinghelper.update_elo(game.red, game.green, game.winner, GameType.SM5)
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
        
async def log_laserball_game(game: Game):
    await sql.execute("INSERT INTO `games` (winner, type) VALUES (%s, %s);", (game.winner, game.type.value))
    
    # gets id of the inserted game
    last_row = await sql.fetchone("SELECT LAST_INSERT_ID();")
    game_id = last_row[0]
    
    game.red, game.green = await ratinghelper.update_elo(game.red, game.blue, game.winner, GameType.SM5)
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