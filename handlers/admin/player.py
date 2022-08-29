from helpers.userhelper import get_median_role_score
from objects import GameType, Team
from utils import render_template
from helpers import gamehelper
from objects import Player
from shared import routes
from aiohttp import web
from shared import sql

@routes.get("/admin/player/{id}")
async def admin_player_get(request: web.Request):
    id = request.match_info["id"]

    player = await Player.from_player_id(id)

    if not player:
        player = await Player.from_name(id)  # could be codename

        if not player:
            raise web.HTTPNotFound(reason="Invalid ID or codename")
    
    return await render_template(request, "admin/player.html",
                                player=player,
                                role_plot_data_player=await get_median_role_score(player),
                                role_plot_data_world=await get_median_role_score(),
                                red_teams_sm5=await gamehelper.get_teams(GameType.SM5, Team.RED, player.player_id),
                                green_teams_sm5=await gamehelper.get_teams(GameType.SM5, Team.GREEN, player.player_id),
                                red_teams_laserball=await gamehelper.get_teams(GameType.LASERBALL, Team.RED, player.player_id),
                                blue_teams_laserball=await gamehelper.get_teams(GameType.LASERBALL, Team.BLUE, player.player_id),
                                sm5_win_percent=await gamehelper.get_win_percent(GameType.SM5, player.player_id),
                                laserball_win_percent=await gamehelper.get_win_percent(GameType.LASERBALL, player.player_id),
                                win_percent=await gamehelper.get_win_percent_overall(player.player_id))

@routes.post("/admin/player")
async def admin_player_post(request: web.Request):
    data = await request.post()
    user = data["userid"]
    raise web.HTTPFound(f"/admin/player/{user}")