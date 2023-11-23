from sanic import Request
from shared import app
from utils import render_template
from helpers import userhelper
from helpers.statshelper import sentry_trace

@app.get("/")
@sentry_trace
async def index(request: Request) -> str:
    return await render_template(request,
        "index.html",
        role_plot_data=await userhelper.get_median_role_score(),
    )