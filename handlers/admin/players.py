from sanic import Request
from helpers import gamehelper, userhelper
from utils import render_template
from shared import app

@app.get("/admin/players")
async def admin_players(request: Request):
    page = int(request.args.get("page", 0))
    
    return await render_template(
        request,
        "admin/players.html",
        players=await userhelper.get_players(15, 15 * page),
        page=page
    )