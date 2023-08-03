from sanic import Request
from shared import app
from utils import render_template
from db.models import SM5Game, EntityEnds, SM5Stats, LaserballGame
from sanic import exceptions
from helpers.statshelper import sentry_trace


@app.get("/game/<type:str>/<id:int>/")
@sentry_trace
async def game_index(request: Request, type: str, id: int):

    
    if type == "sm5":
        game = await SM5Game.filter(id=id).first()
        
        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")
        return await render_template(
            request, "game/sm5.html",
            game=game, EntityEnds=EntityEnds,
            SM5Stats=SM5Stats, fire_score=await game.get_red_score(),
            earth_score=await game.get_green_score()
        )
    elif type == "lb":
        game = await LaserballGame.filter(id=id).first()
        
        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")
        return await render_template(
            request, "game/laserball.html",
            game=game, EntityEnds=EntityEnds,
            fire_score=await game.get_red_score(),
            earth_score=await game.get_blue_score()
        )