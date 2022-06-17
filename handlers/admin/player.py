from aiohttp import web
from helpers import gamehelper, userhelper
from utils import render_template
from shared import routes
from objects import Player

@routes.get("/admin/player/{id}")
async def admin_player_get(request: web.Request):
    id = request.match_info["id"]
    try:
        player = await Player.from_player_id(id)
    except ValueError:
        try:
            player = await Player.from_name(id)  # could be codename
        except ValueError:
            raise web.HTTPNotFound(reason="Invalid ID")
    return await render_template(request, "admin/player.html", player=player)

@routes.post("/admin/player")
async def admin_player_post(request: web.Request):
    data = await request.post()
    user = data["userid"]
    raise web.HTTPFound(f"/admin/player/{user}")