from sanic import Request
from shared import app
from utils import render_template
from helpers.statshelper import sentry_trace

@app.get("/game/<type:str>/<id:int>/replay")
@sentry_trace
async def game_replay(request: Request, type: str, id: int) -> str:
    if type == "sm5":
        return await render_template(request, "game/replay_sm5.html", game_id=id)
    elif type in "laserball":
        return await render_template(request, "game/replay_laserball.html", game_id=id)
        