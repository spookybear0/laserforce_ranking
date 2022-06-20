from aiohttp import web
from helpers import gamehelper
from shared import routes

@routes.get("/admin/recaculate")
async def recaculate():
    await gamehelper.relog_all_games()
    return web.HTTPOk()