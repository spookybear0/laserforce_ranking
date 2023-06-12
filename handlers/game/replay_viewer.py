from sanic import Request
from shared import app
from helpers import ratinghelper
from utils import render_template
from objects import Game, Team, GameType
from parse_tdf import parse_sm5_game as parse_sm5_game_
from helpers.tdfhelper import parse_sm5_game

@app.get("/game/<id:int>/replay")
async def replay_viewer(request: Request, id: int):
    return await render_template(request, "replay.html", game_id=id)