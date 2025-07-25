from sanic import Request
from sanic.log import logger

from helpers import userhelper
from helpers.cachehelper import cache_template, precache_template
from helpers.statshelper import sentry_trace
from shared import app
from utils import render_cached_template


@app.get("/")
@sentry_trace
@cache_template()
@precache_template()
async def index(request: Request) -> str:
    logger.info("Loading index page")

    return await render_cached_template(request,
                                        "index.html",
                                        role_plot_data=await userhelper.get_median_role_score(),
                                        )
