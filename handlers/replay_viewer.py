from sanic import Request
from shared import app
from helpers import ratinghelper
from utils import render_template
from objects import Game, Team, GameType
from parse_tdf import parse_sm5_game

@app.get("/replay_viewer")
async def replay_viewer(request: Request):
    game = parse_sm5_game("D:\\code\\python\\projects\\laserforce_ranking\\sm5_tdf\\4-2_20210713191932_-_Space_Marines_5_Tournament.tdf")
    return await render_template(request, "replay_viewer.html", game=game)