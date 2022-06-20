from aiohttp import web
from helpers import gamehelper
from shared import routes

@routes.get("/admin/recalculate")
async def recalculate():
    await gamehelper.relog_all_games()
    return web.HTTPOk()