from sanic import Request
from shared import app
from utils import render_template
from helpers.statshelper import sentry_trace

@sentry_trace
@app.get("/game/<id:int>/replay")
async def game_replay(request: Request, id: int):
    return await render_template(request, "game/replay.html", game_id=id)