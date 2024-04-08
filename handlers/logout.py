from sanic import Request, exceptions, response
from shared import app
from utils import render_template
from db.player import Player
from sanic.log import logger
from helpers.cachehelper import flush_cache

@app.get("/logout")
async def logout(request: Request) -> str:
    logger.info("Logging out user")

    logger.debug("Clearing session data")

    request.ctx.session["codename"] = None
    request.ctx.session["player_id"] = None
    request.ctx.session["permissions"] = None

    logger.debug("Rendering logout page")

    flush_cache(flush_queryset=False)

    # redirect to previous page
    return response.redirect(request.ctx.session.get("previous_page", "/"))