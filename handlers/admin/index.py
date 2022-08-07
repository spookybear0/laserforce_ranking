from aiohttp import web
from helpers import gamehelper, userhelper, ratinghelper
from utils import render_template
from shared import routes
from objects import GameType, Team

@routes.get("/admin")
async def admin(request: web.Request):
    total_players = await userhelper.get_total_players()
    total_games = await gamehelper.get_total_games()
    total_games_played = await gamehelper.get_total_games_played()

    return await render_template(
        request,
        "admin/admin.html",
        total_players=total_players,
        total_games=total_games,
        total_games_played=total_games_played,
        red_wins=await gamehelper.get_wins(GameType.SM5, Team.RED),
        green_wins=await gamehelper.get_wins(GameType.SM5, Team.GREEN)
    )