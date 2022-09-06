from sanic import Request
from shared import app
from utils import render_template
from helpers import userhelper
import objects

@app.get("/players")
async def index(request: Request):
    page = int(request.args.get("page", 0))
    return await render_template(request,
                                "players.html",
                                players=await userhelper.get_top(objects.GameType.SM5, 25, 25 * page),
                                page=page)