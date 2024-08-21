from sanic import Request
from sanic.log import logger

from shared import app
from utils import render_template


@app.get("/about")
async def about(request: Request) -> str:
    logger.info("Loading about page")
    return await render_template(request, "about.html")
