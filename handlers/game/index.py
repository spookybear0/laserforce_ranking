from sanic import Request
from shared import app
from utils import render_template
from db.models import SM5Game, EntityEnds, SM5Stats
from sanic import exceptions
from helpers.statshelper import sentry_trace

@sentry_trace
@app.get("/game/<id:int>/")
async def game_index(request: Request, id: int):
    game = await SM5Game.filter(id=id).first()
    
    if not game:
        raise exceptions.NotFound("Not found: Invalid game ID")
    
    return await render_template(
        request, "game/index.html",
        game=game, EntityEnds=EntityEnds,
        SM5Stats=SM5Stats, fire_score=await game.get_red_score(),
        earth_score=await game.get_green_score(), print=print
    )