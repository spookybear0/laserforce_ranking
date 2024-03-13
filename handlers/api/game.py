

from sanic import Request
from shared import app
from utils import render_template
from db.sm5 import SM5Game
from db.laserball import LaserballGame
from sanic import exceptions, response
from sanic.log import logger
from helpers.statshelper import sentry_trace

@app.get("/api/game/<type_:str>/<id:int>/tdf")
@sentry_trace
async def api_game_tdf(request: Request, type_: str, id: int) -> str:
    """
    Returns a tdf file for the game
    """
    logger.info(f"Game {id} requested from api")

    if type_ == "sm5":
        game = await SM5Game.filter(id=id).first()
    elif type_ == "laserball":
        game = await LaserballGame.filter(id=id).first()
    else:
        raise exceptions.BadRequest("Invalid game type!", status_code=400)

    if game is None:
        raise exceptions.NotFound("Game not found!", status_code=404)
    
    full_type_name = "sm5" if type_ == "sm5" else "laserball"
    
    # return the tdf file
    return await response.file(f"{full_type_name}_tdf/{game.tdf_name}", filename=game.tdf_name)

@app.get("/api/game/<type_:str>/<id:int>/json")
@sentry_trace
async def api_game_json(request: Request, type_: str, id: int) -> str:
    """
    This is meant for the web frontend only to request a game from the api
    """
    logger.info(f"Game {id} requested from api")

    if type_ == "sm5":
        game = await SM5Game.filter(id=id).first()
    elif type_ == "laserball":
        game = await LaserballGame.filter(id=id).first()
    else:
        raise exceptions.BadRequest("Invalid game type!", status_code=400)

    if game is None:
        raise exceptions.NotFound("Game not found!", status_code=404)

    return response.json(await game.to_dict())