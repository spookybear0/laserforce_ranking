from helpers import userhelper, gamehelper
from aiohttp import web
from shared import routes
from utils import render_template
from objects import ALL_ROLES, GameType, Team, Game
import traceback
import bcrypt

@routes.get("/log_laserball")
async def log_laserball_get(request: web.Request):
    return await render_template(request, "log_laserball.html")

@routes.post("/log_laserball")
async def log_laserball_post(request: web.Request):
    data = await request.post()

    # super secure am i right boys

    pw = b"$2b$12$vHna8FDzqxkh5MblhUg.quyu6kj5uOnBL2dG6yC/9rvT4xAlsOnoe"

    if not bcrypt.checkpw(bytes(data["password"], encoding="utf-8"), pw):
        return web.Response(text="403: Access Denied! (you have been reported to the fbi)")

    winner = data["winner"]  # blue or red
    
    # setup player lists
    red_players = []
    red_game_players = []
    
    blue_players = []
    blue_game_players = []

    # get form data for red team (turn it into objects)
    try:
        await userhelper.get_data_from_form_laserball(red_players, red_game_players, data, Team.RED)
    except ValueError:
        return web.Response(text="401: Error, invalid data! (red team)")
    
    # get form data for blue team (turn it into objects)
    try:
        await userhelper.get_data_from_form_laserball(blue_players, blue_game_players, data, Team.BLUE)
    except ValueError:
        return web.Response(text="401: Error, invalid data! (blue team)")
        blue_players.append(player)

    if len(red_players) == 0 or len(blue_players) == 0:
        return web.Response(text="401: Error, invalid data! (invalid teams)")

    players = [*red_players, *blue_players]

    for player in players:
        if len(player.player_id.split("-")) != 3:
            return web.Response(text="401: Error, invalid data! (id)")

    if not winner in ["blue", "red"]:
        return web.Response(text="401: Error, invalid data! (no winner)")

    game = Game(0, Team(winner), GameType.LASERBALL)  # game_id is 0 becaue its undefined
    game.players = players
    game.blue = blue_players
    game.red = red_players

    try:
        await gamehelper.log_laserball_game(game)
    except Exception as e:
        traceback.print_exc()
        return web.Response(text="500: Error, game was not logged!")
    else:
        return web.Response(text="200: Logged!")