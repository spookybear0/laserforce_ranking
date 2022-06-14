from aiohttp import web
from shared import routes
from utils import render_template
from helpers import rfidhelper

@routes.get("/rfid")
async def rfid(request: web.Request):
    return await render_template(request, "rfid.html")

@routes.post("/rfid")
async def rfid_post(request: web.Request):
    data = await request.post()
    hex = data.get("hex")
    decimal = data.get("decimal")

    if hex:
        return web.Response(text=rfidhelper.to_decimal(hex))
    elif decimal:
        return web.Response(text=rfidhelper.to_hex(decimal))
    return web.Response(text="You need to add data to the form")