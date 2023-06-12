

from sanic import Request
from shared import app
from utils import render_template
from db.models import SM5Game
from sanic import exceptions, response
from sanic.log import logger

@app.get("/api/game/<id:int>")
async def api_game(request: Request, id: int):
    logger.info(f"Game {id} requested")
    game = await SM5Game.filter(id=id).first()

    if game is None:
        return exceptions.NotFound("Game not found!", status_code=404)

    return response.json(await game.to_dict())