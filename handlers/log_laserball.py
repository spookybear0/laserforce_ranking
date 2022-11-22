from helpers import userhelper, gamehelper
from sanic import Request, exceptions, response
from shared import app
from utils import render_template, get_post
from objects import ALL_ROLES, GameType, Team, Game
import bcrypt

@app.get("/log_laserball")
async def log_laserball_get(request: Request):
    return await render_template(request, "log_laserball.html")

@app.post("/log_laserball")
async def log_laserball_post(request: Request):
    data = get_post(request)

    # super secure am i right boys

    pw = b"$2b$12$vHna8FDzqxkh5MblhUg.quyu6kj5uOnBL2dG6yC/9rvT4xAlsOnoe"

    if not bcrypt.checkpw(bytes(data["password"], encoding="utf-8"), pw):
        raise exceptions.Forbidden("Access Denied! (you have been reported to the fbi)")

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
        raise exceptions.BadRequest("Error, invalid data! (red team)")
    
    # get form data for blue team (turn it into objects)
    try:
        await userhelper.get_data_from_form_laserball(blue_players, blue_game_players, data, Team.BLUE)
    except ValueError:
        raise exceptions.BadRequest("Error, invalid data! (blue team)")

    if len(red_players) == 0 or len(blue_players) == 0:
        raise exceptions.BadRequest("Error, invalid data! (invalid teams)")

    players = [*red_players, *blue_players]

    if not winner in ["blue", "red"]:
        raise exceptions.BadRequest("Error, invalid data! (no winner)")

    game = Game(0, Team(winner), GameType.LASERBALL)  # game_id is 0 becaue its undefined
    game.players = players
    game.blue = blue_players
    game.red = red_players

    await gamehelper.log_laserball_game(game)
    
    return response.text("Logged!")