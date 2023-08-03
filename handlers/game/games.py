from sanic import Request
from shared import app
from utils import render_template
from db.models import SM5Game, LaserballGame
from tortoise.expressions import F
from helpers.statshelper import sentry_trace

@app.get("/games")
@sentry_trace
async def index(request: Request):
    page = int(request.args.get("page", 0))

    # get both sm5 and laserball games

    sm5_games = await SM5Game.all().order_by("-start_time").limit(10).offset(10 * page)
    lb_games = await LaserballGame.all().order_by("-start_time").limit(10).offset(10 * page)

    # sort by date

    games = sorted(sm5_games + lb_games, key=lambda x: x.start_time, reverse=True)

    return await render_template(
        request,
        "game/games.html",
        games=games,
        page=page
    )