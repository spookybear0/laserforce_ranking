from helpers import userhelper, gamehelper
from aiohttp import web
from shared import routes
from utils import render_template
from objects import ALL_ROLES, GameType, Team, Game
import traceback
import bcrypt
from traceback import print_exc

@routes.get("/log_sm5")
async def log_sm5_get(request: web.Request):
    return await render_template(request, "log_sm5.html")

@routes.post("/log_sm5")
async def log_sm5_post(request: web.Request):
    data = await request.post()

    # super secure am i right boys

    pw = b"$2b$12$vHna8FDzqxkh5MblhUg.quyu6kj5uOnBL2dG6yC/9rvT4xAlsOnoe"

    if not bcrypt.checkpw(bytes(data["password"], encoding="utf-8"), pw):
        return web.Response(text="403: Access Denied! (you have been reported to the fbi)")
        
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
        print_exc()
        return web.Response(text="401: Error, invalid data! (red team)")
    
    # get form data for green team (turn it into objects)
    try:
        await userhelper.get_data_from_form_sm5(green_players, green_game_players, data, Team.GREEN)
    except ValueError:
        print_exc()
        return web.Response(text="401: Error, invalid data! (green team)")
        green_players.append(player)
        
    # make sure input is correct
    if len(red_players) == 0 or len(green_players) == 0:
        print_exc()
        return web.Response(text="401: Error, invalid data! (invalid teams)")

    players = [*red_players, *green_players]

    for player in players:
        if not player.game_player.role.value in ALL_ROLES:
            return web.Response(text="401: Error, invalid data! (role)")
        if (len(player.player_id.split("-")) != 3) and not player.id == -1:
            return web.Response(text="401: Error, invalid data! (id)")

    if not winner in ["green", "red"]:
        return web.Response(text="401: Error, invalid data! (no winner)")

    # assign all players to the game obj
    game = Game(0, winner, GameType.SM5)  # game_id is 0 becaue its undefined
    game.players = players
    game.green = green_players
    game.red = red_players

    try:
        await gamehelper.log_sm5_game(game)
    except Exception as e:
        traceback.print_exc() # debug info
        return web.Response(text="500: Error, game was not logged!")
    
    return web.Response(text="200: Logged!")