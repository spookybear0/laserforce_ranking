from sanic import Request
from helpers.statshelper import sentry_trace
from shared import app
from sanic.log import logger
from sanic import exceptions, response
from db.player import Player

@app.post("/api/login")
@sentry_trace
async def api_login(request: Request) -> str:
    # get the codename and password from the request

    codename = request.json.get("codename")
    password = request.json.get("password")

    if codename is None or password is None:
        return response.json({"error": "Invalid codename or password"}, status=401)

    # check if the codename and password are correct

    player = await Player.filter(codename=codename).first()

    if player is None or not player.check_password(password):
        return response.json({"error": "Invalid codename or password"}, status=401)
    
    request.ctx.session["codename"] = player.codename
    request.ctx.session["player_id"] = player.player_id
    request.ctx.session["permissions"] = player.permissions
    
    #TODO: maybe generate a token or something
    return response.json({"status": "ok"})