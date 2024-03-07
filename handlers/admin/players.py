from sanic import Request
from shared import app
from utils import render_template, admin_only
from db.models import Player
from tortoise.expressions import F

@app.get("/admin/players")
@admin_only
async def admin_players(request: Request) -> str:
    page = int(request.args.get("page", 0))

    # handle negative page numbers

    if page < 0:
        page = 0

    return await render_template(request,
        "admin/players.html",
        players=await Player.filter().limit(25).offset(25 * page)
            .annotate(ordinal=F("sm5_mu") - 3 * F("sm5_sigma")).order_by("-ordinal"),
        page=page,
    )
