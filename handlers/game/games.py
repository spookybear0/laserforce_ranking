from sanic import Request

from db.laserball import LaserballGame
from db.sm5 import SM5Game
from helpers.cachehelper import cache_template
from helpers.statshelper import sentry_trace
from shared import app
from utils import render_cached_template

GAMES_PER_PAGE = 15


@app.get("/games")
@sentry_trace
@cache_template()
async def index(request: Request) -> str:
    page = int(request.args.get("page", 0))
    mode = request.args.get("mode", "sm5")
    sort = int(request.args.get("sort", "0"))
    sort_direction = request.args.get("sort_dir", "desc")

    # sorting

    order_by = "start_time"

    if sort == 0:
        order_by = "start_time"
    elif sort == 1:  # winner team
        order_by = "winner_color"
    elif sort == 2:  # ended early
        order_by = "ended_early"
    elif sort == 3:  # ranked
        order_by = "ranked"

    order_by = "-" + order_by if sort_direction == "desc" else order_by

    # handle negative page numbers

    if page < 0:
        page = 0

    # get both sm5 and laserball games

    sm5_games = await SM5Game.all().order_by(order_by).limit(GAMES_PER_PAGE).offset(GAMES_PER_PAGE * page)
    laserball_games = await LaserballGame.all().order_by(order_by).limit(GAMES_PER_PAGE).offset(GAMES_PER_PAGE * page)

    return await render_cached_template(
        request,
        "game/games.html",
        sm5_games=sm5_games,
        laserball_games=laserball_games,
        page=page,
        mode=mode,
        sort=sort,
        sort_dir=sort_direction
    )
