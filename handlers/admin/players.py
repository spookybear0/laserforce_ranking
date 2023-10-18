from sanic import Request
from shared import app
from utils import render_template, admin_only

@app.get("/admin/players")
@admin_only
async def admin_players(request: Request):
    return await render_template(request,
        "admin/players.html",
    )
