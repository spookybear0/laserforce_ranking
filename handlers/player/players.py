from sanic import Request
from tortoise.expressions import F

from db.player import Player
from helpers.cachehelper import cache_template, precache_template
from helpers.statshelper import sentry_trace
from shared import app
from utils import render_cached_template


@app.get("/players")
@sentry_trace
@cache_template()
@precache_template()
async def players(request: Request) -> str:
    page = request.args.get("page", 0)
    sort = request.args.get("sort", "2")
    sort_direction = request.args.get("sort_dir", "desc")

    # Validate and convert page number to integer

    try:
        page = int(page)
    except ValueError:
        raise ValueError("Invalid page number")
    
    # Validate sort parameter
    try:
        sort = int(sort)
    except ValueError:
        raise ValueError("Invalid sort parameter")
    
    # Validate sort direction

    if sort_direction not in ["asc", "desc"]:
        raise ValueError('Invalid sort direction. Use "asc" or "desc".')

    # handle negative page numbers

    if page < 0:
        page = 0

    order_by = "sm5_ord"

    if sort == 0:
        order_by = "codename"
    elif sort == 1:
        order_by = "player_id"
    elif sort == 2:
        order_by = "sm5_ord"
    elif sort == 3:
        order_by = "laserball_ord"

    order_by = "-" + order_by if sort_direction == "desc" else order_by

    return await render_cached_template(request,
                                        "player/players.html",
                                        players=await Player.filter().limit(25).offset(25 * page)
                                        .annotate(sm5_ord=F("sm5_mu") - 3 * F("sm5_sigma"),
                                                  laserball_ord=F("laserball_mu") - 3 * F("laserball_sigma")
                                                  ).order_by(order_by),
                                        page=page,
                                        sort=sort,
                                        sort_dir=sort_direction
                                        )
