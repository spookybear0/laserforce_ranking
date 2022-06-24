from aiohttp import web
from objects import GameType, Team
from helpers import gamehelper, userhelper
from utils import render_template
from shared import routes
from objects import Player

@routes.get("/admin/player/{id}")
async def admin_player_get(request: web.Request):
    id = request.match_info["id"]

    player = await Player.from_player_id(id)

    if not player:
        player = await Player.from_name(id)  # could be codename

        if not player:
            raise web.HTTPNotFound(reason="Invalid ID")
    
    return await render_template(request, "admin/player.html",
                                player=player,
                                red_wins=await gamehelper.get_teams(GameType.SM5, Team.RED, player.player_id),
                                green_wins=await gamehelper.get_teams(GameType.SM5, Team.GREEN, player.player_id))

@routes.post("/admin/player")
async def admin_player_post(request: web.Request):
    data = await request.post()
    user = data["userid"]
    raise web.HTTPFound(f"/admin/player/{user}")