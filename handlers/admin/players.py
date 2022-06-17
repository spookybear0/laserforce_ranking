from aiohttp import web
from helpers import gamehelper, userhelper
from utils import render_template
from shared import routes

@routes.get("/admin/players")
async def admin_players(request: web.Request):
    page = int(request.rel_url.query.get("page", 0))
    
    return await render_template(
        request,
        "admin/players.html",
        players=await userhelper.get_players(15, 15 * page),
        page=page
    )