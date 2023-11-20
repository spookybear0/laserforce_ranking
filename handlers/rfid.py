from sanic import Request, exceptions, HTTPResponse
from shared import app
from utils import render_template, get_post
from helpers import rfidhelper

@app.get("/rfid")
async def rfid(request: Request) -> str:
    return await render_template(request, "rfid.html")

@app.post("/rfid")
async def rfid_post(request: Request) -> str:
    print(request.form)
    data = get_post(request)

    # data.get() wont work for some reason so we have to do this
    hex = None
    if "hex" in data:
        hex = data["hex"]

    decimal = None
    if "decimal" in data:
        decimal = data["decimal"]

    if hex:
        return HTTPResponse(str(rfidhelper.to_decimal(hex)))
    elif decimal:
        return HTTPResponse(str(rfidhelper.to_hex(decimal)))

    raise exceptions.BadRequest("Form data must be filled out.")