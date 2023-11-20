

from sanic import Request
from shared import app
from utils import render_template
from db.models import SM5Game, LaserballGame
from sanic import exceptions, response
from sanic.log import logger
from helpers.statshelper import sentry_trace

@app.get("/api/game/<type:str>/<id:int>")
@sentry_trace
async def api_game(request: Request, type: str, id: int) -> str:
    logger.info(f"Game {id} requested")

    if type == "sm5":
        game = await SM5Game.filter(id=id).first()
    elif type == "lb":
        game = await LaserballGame.filter(id=id).first()
    else:
        raise exceptions.BadRequest("Invalid game type!", status_code=400)

    if game is None:
        raise exceptions.NotFound("Game not found!", status_code=404)

    return response.json(await game.to_dict())