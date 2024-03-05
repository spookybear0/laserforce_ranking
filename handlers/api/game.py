

from sanic import Request
from shared import app
from utils import render_template
from db.models import SM5Game, LaserballGame
from sanic import exceptions, response
from sanic.log import logger
from helpers.statshelper import sentry_trace

@app.get("/api/game/<type_:str>/<id:int>")
@sentry_trace
async def api_game(request: Request, type_: str, id: int) -> str:
    """
    Returns a tdf file for the game
    """
    logger.info(f"Game {id} requested from api")

    if type_ == "sm5":
        game = await SM5Game.filter(id=id).first()
    elif type_ == "lb":
        game = await LaserballGame.filter(id=id).first()
    else:
        raise exceptions.BadRequest("Invalid game type!", status_code=400)

    if game is None:
        raise exceptions.NotFound("Game not found!", status_code=404)
    
    full_type_name = "sm5" if type_ == "sm5" else "laserball"
    
    # return the tdf file
    return await response.file(f"{full_type_name}_tdf/{game.tdf_name}", filename=game.tdf_name)

@app.get("/api/game_json/<type_:str>/<id:int>")
@sentry_trace
async def api_game_json(request: Request, type_: str, id: int) -> str:
    """
    This is meant for the web frontend only to request a game from the api
    """
    logger.info(f"Game {id} requested from api")

    if type_ == "sm5":
        game = await SM5Game.filter(id=id).first()
    elif type_ == "lb":
        game = await LaserballGame.filter(id=id).first()
    else:
        raise exceptions.BadRequest("Invalid game type!", status_code=400)

    if game is None:
        raise exceptions.NotFound("Game not found!", status_code=404)

    return response.json(await game.to_dict())