from sanic import Request, exceptions, response
from shared import app
from utils import render_template
from db.models import Player

@app.get("/login")
async def login(request: Request):
    return await render_template(request, "login.html")

@app.post("/login")
async def login_post(request: Request):
    codename = request.form.get("codename")
    password = request.form.get("password")

    if not codename or not password:
        # TODO: better error message
        raise exceptions.BadRequest("Missing codename or password")
    
    player = await Player.filter(codename=codename).first()

    if not player:
        raise exceptions.BadRequest("Invalid codename or password")
    
    if not player.check_password(password):
        raise exceptions.BadRequest("Invalid codename or password")
    
    request.ctx.session["codename"] = player.codename
    request.ctx.session["player_id"] = player.player_id
    request.ctx.session["permissions"] = player.permissions

    return response.redirect("/")