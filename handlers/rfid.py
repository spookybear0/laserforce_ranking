from sanic import Request, exceptions, HTTPResponse

from helpers import userhelper
from shared import app
from utils import render_template


# hidden page, i don't really use this anymore

@app.get("/rfid")
async def rfid(request: Request) -> str:
    return await render_template(request, "rfid.html")


@app.post("/rfid")
async def rfid_post(request: Request) -> str:
    data = request.form

    hex = None
    if "hex" in data:
        hex = data["hex"][0]

    decimal = None
    if "decimal" in data:
        decimal = data["decimal"][0]

    if hex:
        return HTTPResponse(str(userhelper.rfid_to_decimal(hex)))
    elif decimal:
        return HTTPResponse(str(userhelper.rfid_to_hex(decimal)))

    raise exceptions.BadRequest("Form data must be filled out.")
