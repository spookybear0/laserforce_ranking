from sanic import Request
from shared import app
from utils import render_template
from db.models import SM5Game, EntityEnds, EntityStarts, SM5Stats, LaserballGame, LaserballStats
from sanic import exceptions
from helpers.statshelper import sentry_trace
from numpy import arange
import math
from typing import List

@app.get("/game/<type:str>/<id:int>/")
@sentry_trace
async def game_index(request: Request, type: str, id: int):

    if type == "sm5":
        game: SM5Game = await SM5Game.filter(id=id).first()

        players_matchmake = []
        entity_starts: List[EntityStarts] = await game.entity_starts
        for i, player in enumerate(entity_starts):
            if player.type != "player":
                continue

            players_matchmake.append(player.name)

        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")
        return await render_template(
            request, "game/sm5.html",
            game=game, EntityEnds=EntityEnds,
            SM5Stats=SM5Stats, fire_score=await game.get_red_score(),
            earth_score=await game.get_green_score(),
            score_chart_labels=[t for t in arange(0, 900000//1000//60+0.5, 0.5)],
            score_chart_data_red=[await game.get_red_score_at_time(t) for t in range(0, 900000+25000, 25000)],
            score_chart_data_green=[await game.get_green_score_at_time(t) for t in range(0, 900000+25000, 25000)],
            win_chance=await game.get_win_chance_at_time(),
            draw_chance=await game.get_draw_chance_at_time(),
            players_matchmake=players_matchmake
        )
    elif type == "lb":
        game = await LaserballGame.filter(id=id).first()

        players_matchmake = []
        entity_starts: List[EntityStarts] = await game.entity_starts
        for i, player in enumerate(entity_starts):
            if player.type != "player":
                continue

            players_matchmake.append(player.name)
        
        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")
        return await render_template(
            request, "game/laserball.html",
            game=game, EntityEnds=EntityEnds, LaserballStats=LaserballStats,
            fire_score=await game.get_red_score(),
            ice_score=await game.get_blue_score(),
            score_chart_labels=[{"x": t, "y": await game.get_rounds_at_time(t*60*1000)} for t in arange(0, 900000//1000//60+0.5, 0.5)],
            score_chart_data_red=[await game.get_red_score_at_time(t) for t in range(0, 900000+25000, 25000)],
            score_chart_data_blue=[await game.get_blue_score_at_time(t) for t in range(0, 900000+25000, 25000)],
            score_chart_data_rounds=[await game.get_rounds_at_time(t) for t in range(0, 900000+25000, 25000)],
            win_chance=await game.get_win_chance_at_time(),
            draw_chance=await game.get_draw_chance_at_time(),
            game_end_time_decimal=min(math.ceil((await game.scores.order_by("-time").first()).time/1000/60*2)/2, 15),
            players_matchmake=players_matchmake
        )
    else:
        raise exceptions.NotFound("Not found: Invalid game type")