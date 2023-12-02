from sanic import Request
from shared import app
from utils import render_template
from sanic.log import logger

@app.get("/about")
async def about(request: Request) -> str:
    logger.info("Loading about page")
    return await render_template(request, "about.html")