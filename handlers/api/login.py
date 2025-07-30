from sanic import Request
from sanic import response

from db.player import Player
from helpers.statshelper import sentry_trace
from handlers.api import api_bp
from sanic_ext import openapi
from sanic_ext.extensions.openapi.definitions import RequestBody, Response


@api_bp.post("/login")
@openapi.definition(
    summary="Login",
    description="Logs in a player with codename and password. This allows the player to access their session and perform actions that require authentication.",
    response=[
        Response(
            {"application/json": {"type": "object", "properties": {"status": {"type": "string"}}}},
            description="Login successful",
            status=200,
        ),
        Response(
            {"application/json": {"type": "object", "properties": {"error": {"type": "string"}}}},
            description="Invalid codename or password",
            status=401,
        ),
        Response(
            {"application/json": {"type": "object", "properties": {"error": {"type": "string"}}}},
            description="Internal Server Error",
            status=500,
        ),
    ],
    body=RequestBody(
        content={
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "codename": {"type": "string"},
                        "password": {"type": "string"},
                    },
                    "required": ["codename", "password"],
                }
            }
        }
    ),
)
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

    # TODO: maybe generate a token or something
    return response.json({"status": "ok"})
