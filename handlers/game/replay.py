from sanic import Request
from sanic import exceptions

from helpers.statshelper import sentry_trace
from shared import app
from utils import render_template
from db.sm5 import SM5Game
from db.laserball import LaserballGame


@app.get("/game/<type:str>/<id:int>/replay")
@sentry_trace
async def game_replay(request: Request, type: str, id: int) -> str:
    if type == "sm5":
        return await render_template(request, "game/replay.html", game_type=type, game_id=id, game=await SM5Game.filter(id=id).first())
    elif type in "laserball":
        return await render_template(request, "game/replay.html", game_type=type, game_id=id, game=await LaserballGame.filter(id=id).first())
    raise exceptions.BadRequest("Invalid game type")
