from objects import GameType, Team
from helpers.statshelper import barplot
from utils import render_template
from helpers import gamehelper, ratinghelper
from objects import Player
from shared import routes
from aiohttp import web
from shared import sql
from io import BytesIO
import base64

@routes.get("/admin/player/{id}")
async def admin_player_get(request: web.Request):
    id = request.match_info["id"]

    player = await Player.from_player_id(id)

    if not player:
        player = await Player.from_name(id)  # could be codename

        if not player:
            raise web.HTTPNotFound(reason="Invalid ID or codename")

    data = []
    
    for role in ["commander", "heavy", "scout", "ammo", "medic"]:
        q = await sql.fetchone("""SELECT AVG(score) FROM sm5_game_players
                                  WHERE player_id = %s AND role = %s""",
                              (player.player_id, role))
        if q[0]:
            data.append(int(q[0]))
        else:
            data.append(0)
    
    role_plot = barplot(["Commander", "Heavy", "Scout", "Ammo", "Medic"],
                        data,
                        f"Average score in relation to role\n{player.player_id}",
                        "Role", "Average score")

    role_plot_b64 = BytesIO()
    role_plot.save(role_plot_b64, "PNG")
    role_plot_b64 = base64.b64encode(role_plot_b64.getvalue())
    
    return await render_template(request, "admin/player.html",
                                player=player,
                                role_plot=role_plot_b64.decode("utf-8"),
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