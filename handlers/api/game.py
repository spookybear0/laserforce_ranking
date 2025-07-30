from sanic import Request
from sanic import exceptions, response
from sanic.log import logger

from db.laserball import LaserballGame
from db.sm5 import SM5Game
from helpers.cachehelper import cache
from helpers.statshelper import sentry_trace
from handlers.api import api_bp
from sanic_ext import openapi
from sanic_ext.extensions.openapi.definitions import RequestBody, Response


@api_bp.get("/game/<type:str>/<id:int>/tdf")
@openapi.definition(
    summary="Get Game TDF",
    description="Returns the TDF file for the specified game type and ID.",
    response=[
        Response({"text/plain": str}, description="TDF file content", status=200),
    ],
    body=RequestBody(
        content={"application/json": {"schema": {"type": "object"}}},
    ),
)
@sentry_trace
async def api_game_tdf(request: Request, type: str, id: int) -> str:
    """
    Returns a tdf file for the game
    """
    logger.info(f"Game {id} requested from api")

    if type == "sm5":
        game = await SM5Game.filter(id=id).first()
    elif type == "laserball":
        game = await LaserballGame.filter(id=id).first()
    else:
        raise exceptions.BadRequest("Invalid game type!")

    if game is None:
        raise exceptions.NotFound("Game not found!")

    full_type_name = "sm5" if type == "sm5" else "laserball"

    # return the tdf file
    try:
        return await response.file(f"{full_type_name}_tdf/{game.tdf_name}", filename=game.tdf_name)
    except FileNotFoundError:
        raise exceptions.NotFound("TDF file not found on server!")


@api_bp.get("/game/<type:str>/<id:int>/json")
# exclude from openapi docs because it's too complex to document properly
# and not meant for public use. TODO: add an updated version that is documented well
@openapi.exclude()
@sentry_trace
@cache()
async def api_game_json(request: Request, type: str, id: int) -> str:
    """
    This is meant for the web frontend only to request a game from the api
    """
    logger.info(f"Game {id} requested from api")

    if type == "sm5":
        game = await SM5Game.filter(id=id).first()
    elif type == "laserball":
        game = await LaserballGame.filter(id=id).first()
    else:
        raise exceptions.BadRequest("Invalid game type!")

    if game is None:
        raise exceptions.NotFound("Game not found!")

    return response.json(await game.to_dict())