from sanic import Request
from shared import app
from utils import render_template
from helpers import gamehelper, userhelper
from objects import GameType, Team
from helpers.statshelper import sentry_trace
from db.models import SM5Game, Player, EntityEnds
from tortoise.expressions import F

@app.get("/")
@sentry_trace
async def index(request: Request):
    total_players = await Player.all().count()
    total_games = await SM5Game.all().count()
    total_games_played = await EntityEnds.all().count()

    sm5_red_wins = await SM5Game.filter(winner=Team.RED, ranked=True).count()
    sm5_green_wins = await SM5Game.filter(winner=Team.GREEN, ranked=True).count()

    

    return await render_template(request,
        "index.html",
        total_players=total_players,
        total_games=total_games,
        total_games_played=total_games_played,
        sm5_red_wins=sm5_red_wins,
        sm5_green_wins=sm5_green_wins,
        #laserball_red_wins=laserball_red_wins,
        #laserball_blue_wins=laserball_blue_wins,
        role_plot_data=await userhelper.get_median_role_score()
    )