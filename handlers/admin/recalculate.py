from sanic import Request, HTTPResponse
from helpers import gamehelper
from shared import app

@app.get("/admin/recalculate")
async def recalculate(request: Request):
    await gamehelper.relog_all_games()
    return HTTPResponse("200 OK.", status=200)