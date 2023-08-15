from sanic import Request
from shared import app
from utils import render_template
from db.models import SM5Game, EntityEnds, SM5Stats, LaserballGame, LaserballStats
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
            earth_score=await game.get_green_score(),
            score_chart_labels=[t for t in range(0, game.mission_duration//1000//60+1, 1)],
            score_chart_data_red=[await game.get_red_score_at_time(t) for t in range(0, game.mission_duration+50000, 50000)],
            score_chart_data_green=[await game.get_green_score_at_time(t) for t in range(0, game.mission_duration+50000, 50000)],
        )
    elif type == "lb":
        game = await LaserballGame.filter(id=id).first()
        
        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")
        return await render_template(
            request, "game/laserball.html",
            game=game, EntityEnds=EntityEnds, LaserballStats=LaserballStats,
            fire_score=await game.get_red_score(),
            ice_score=await game.get_blue_score(),
            score_chart_labels=[t for t in range(0, game.mission_duration//1000//60+1, 1)],
            score_chart_data_red=[await game.get_red_score_at_time(t) for t in range(0, game.mission_duration+50000, 50000)],
            score_chart_data_blue=[await game.get_blue_score_at_time(t) for t in range(0, game.mission_duration+50000, 50000)],
        )