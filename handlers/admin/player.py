from sanic import Request
from shared import app
from utils import render_template, admin_only
from typing import Union
from db.models import Player

@app.get("/admin/player/<id>")
@admin_only
async def admin_player(request: Request, id: Union[int, str]) -> str:
    if type(id) == str:
        # codename
        player = await Player.filter(codename=id).first()
    else: # int
        player = await Player.get_or_none(player_id=id)

    return await render_template(request,
        "admin/player.html",
        player=player,
    )
