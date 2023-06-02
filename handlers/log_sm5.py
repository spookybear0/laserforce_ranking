from helpers import userhelper, gamehelper
from sanic import Request, exceptions, response
from shared import app
from utils import render_template, get_post
from objects import ALL_ROLES, GameType, Team, Game
import bcrypt
from traceback import print_exc

@app.get("/log_sm5")
async def log_sm5_get(request: Request):
    return exceptions.SanicException("Deprecated!", status_code=299)
    return await render_template(request, "log_sm5.html")

@app.post("/log_sm5")
async def log_sm5_post(request: Request):
    return exceptions.SanicException("Deprecated!", status_code=299)
    data = get_post(request)

    # super secure am i right boys

    pw = b"$2b$12$vHna8FDzqxkh5MblhUg.quyu6kj5uOnBL2dG6yC/9rvT4xAlsOnoe"

    if not bcrypt.checkpw(bytes(data["password"][0], encoding="utf-8"), pw):
        raise exceptions.Forbidden("Access Denied! (you have been reported to the fbi)")
        
    winner = data["winner"]  # green or red
    
    # setup player lists
    red_players = []
    red_game_players = []
    
    green_players = []
    green_game_players = []
    
    # get form data for red team (turn it into objects)
    try:
        await userhelper.get_data_from_form_sm5(red_players, red_game_players, data, Team.RED)
    except ValueError:
        raise exceptions.BadRequest("Error, invalid data! (red team)")
    
    # get form data for green team (turn it into objects)
    try:
        await userhelper.get_data_from_form_sm5(green_players, green_game_players, data, Team.GREEN)
    except ValueError:
        raise exceptions.BadRequest("Error, invalid data! (green team)")
        
    # make sure input is correct
    if len(red_players) == 0 or len(green_players) == 0:
        raise exceptions.BadRequest("Error, invalid data! (invalid teams)")

    players = [*red_players, *green_players]

    for player in players:
        if not player.game_player.role.value in ALL_ROLES:
            raise exceptions.BadRequest("Error, invalid data! (role)")

    if not winner in ["green", "red"]:
        raise exceptions.BadRequest("Error, invalid data! (no winner)")

    # assign all players to the game obj
    game = Game(-1, Team(winner), GameType.SM5)  # game_id is -1 becaue its undefined
    game.players = players
    game.green = green_players
    game.red = red_players

    await gamehelper.log_sm5_game(game)
    
    return response.text("Logged!")