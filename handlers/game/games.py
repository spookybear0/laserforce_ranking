from sanic import Request
from shared import app
from utils import render_template
from db.models import SM5Game # add laserball later
from tortoise.expressions import F
from helpers.statshelper import sentry_trace

@app.get("/games")
@sentry_trace
async def index(request: Request):
    page = int(request.args.get("page", 0))
    return await render_template(
        request,
        "game/games.html",
        games=await SM5Game.all().limit(25).offset(25 * page),
        page=page
    )