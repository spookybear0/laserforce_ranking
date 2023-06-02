from sanic import Request
from shared import app
from utils import render_template
from helpers import gamehelper, userhelper
from objects import GameType, Team

@app.get("/")
async def index(request: Request):
    total_players = await userhelper.get_total_players()
    total_games = await gamehelper.get_total_games()
    total_games_played = await gamehelper.get_total_games_played()

    return await render_template(request,
        "index.html",
        total_players=total_players,
        total_games=total_games,
        total_games_played=total_games_played,
        sm5_red_wins=await gamehelper.get_wins(GameType.SM5, Team.RED),
        sm5_green_wins=await gamehelper.get_wins(GameType.SM5, Team.GREEN),
        laserball_red_wins=await gamehelper.get_wins(GameType.LASERBALL, Team.RED),
        laserball_blue_wins=await gamehelper.get_wins(GameType.SM5, Team.BLUE),
        role_plot_data=await userhelper.get_median_role_score()
    )