from sanic import Request, exceptions, response
from shared import app
from utils import render_template
from db.models import Player

@app.get("/logout")
async def logout(request: Request) -> str:
    request.ctx.session["codename"] = None
    request.ctx.session["player_id"] = None
    request.ctx.session["permissions"] = None

    # redirect to previous page
    return response.redirect(request.ctx.session.get("previous_page", "/"))