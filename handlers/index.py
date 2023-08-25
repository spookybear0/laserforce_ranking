from sanic import Request
from shared import app
from utils import render_template
from helpers import statshelper, userhelper
from objects import GameType, Team
from helpers.statshelper import sentry_trace
from db.models import SM5Game, Player, EntityEnds, LaserballGame
from tortoise.expressions import F

@app.get("/")
@sentry_trace
async def index(request: Request):

    return await render_template(request,
        "index.html",
        role_plot_data=await userhelper.get_median_role_score(),
    )