from sanic import Request, exceptions
from shared import app
from utils import render_template
from helpers import rfidhelper

@app.get("/rfid")
async def rfid(request: Request):
    return await render_template(request, "rfid.html")

@app.post("/rfid")
async def rfid_post(request: Request):
    data = await request.post()
    hex = data.get("hex")
    decimal = data.get("decimal")

    if hex:
        return str(rfidhelper.to_decimal(hex))
    elif decimal:
        str(rfidhelper.to_hex(decimal))
    raise exceptions.BadRequest("Form data must be filled out.")