from sanic import Request
from shared import app
from utils import render_template
from db.player import Player
from tortoise.expressions import F
from helpers.statshelper import sentry_trace
from helpers.cachehelper import cache_template

@app.get("/players")
@sentry_trace
@cache_template()
async def index(request: Request) -> str:
    page = int(request.args.get("page", 0))
    sort = int(request.args.get("sort", "2"))
    sort_direction = request.args.get("sort_dir", "desc")

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

    return await render_template(request,
                                "player/players.html",
                                players=await Player.filter().limit(25).offset(25 * page)
                                    .annotate(sm5_ord=F("sm5_mu") - 3 * F("sm5_sigma"),
                                              laserball_ord=F("laserball_mu") - 3 * F("laserball_sigma")
                                            ).order_by(order_by),
                                page=page,
                                sort=sort,
                                sort_dir=sort_direction
                                )