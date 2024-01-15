from sanic import Request
from shared import app
from utils import render_template
from db.models import SM5Game, LaserballGame
from tortoise.expressions import F
from helpers.statshelper import sentry_trace

@app.get("/games")
@sentry_trace
async def index(request: Request) -> str:
    page = int(request.args.get("page", 0))
    mode = request.args.get("mode", "sm5")

    # handle negative page numbers

    if page < 0:
        page = 0

    # get both sm5 and laserball games

    sm5_games = await SM5Game.all().order_by("-start_time").limit(10).offset(10 * page)
    laserball_games = await LaserballGame.all().order_by("-start_time").limit(10).offset(10 * page)

    # sort by date

    sm5_games = sorted(sm5_games, key=lambda x: x.start_time, reverse=True)
    laserball_games = sorted(laserball_games, key=lambda x: x.start_time, reverse=True)

    return await render_template(
        request,
        "game/games.html",
        sm5_games=sm5_games,
        laserball_games=laserball_games,
        page=page,
        mode=mode,
    )