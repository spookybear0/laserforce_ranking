from objects import GameType
from aiohttp import web
from shared import routes
from helpers import userhelper
from utils import render_template

# shows top x
@routes.get("/")
async def index(request: web.Request):
    return await render_template(request, "top.html", players=await userhelper.get_top(GameType.SM5, 50))