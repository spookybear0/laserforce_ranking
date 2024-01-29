from sanic import Request
from shared import app
from utils import render_template, is_admin
from db.models import SM5Game, EntityEnds, EntityStarts, SM5Stats, LaserballGame, LaserballStats
from sanic import exceptions
from helpers.statshelper import sentry_trace
from numpy import arange
import math
from typing import List


async def get_entity_end(entity):
    return await EntityEnds.filter(entity=entity).first()

async def get_sm5stats(entity):
    return await SM5Stats.filter(entity=entity).first()

async def get_laserballstats(entity):
    return await LaserballStats.filter(entity=entity).first()

@app.get("/game/<type:str>/<id:int>/")
@sentry_trace
async def game_index(request: Request, type: str, id: int) -> str:

    if type == "sm5":
        game: SM5Game = await SM5Game.filter(id=id).prefetch_related("entity_starts").first()

        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")

        players_matchmake = []
        entity_starts: List[EntityStarts] = game.entity_starts
        for i, player in enumerate(entity_starts):
            if player.type != "player":
                continue

            players_matchmake.append(player.name)

        return await render_template(
            request, "game/sm5.html",
            game=game, get_entity_end=get_entity_end,
            get_sm5stats=get_sm5stats, fire_score=await game.get_red_score(),
            earth_score=await game.get_green_score(),
            score_chart_labels=[t for t in arange(0, 900000//1000//60+0.5, 0.5)],
            score_chart_data_red=[await game.get_red_score_at_time(t) for t in range(0, 900000+30000, 30000)],
            score_chart_data_green=[await game.get_green_score_at_time(t) for t in range(0, 900000+30000, 30000)],
            win_chance=await game.get_win_chance(),
            win_chance_before_game=await game.get_win_chance_before_game(),
            players_matchmake=players_matchmake,
            is_admin=is_admin(request)
        )
    elif type == "lb":
        game = await LaserballGame.filter(id=id).prefetch_related("entity_starts").first()

        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")

        players_matchmake = []
        entity_starts: List[EntityStarts] = game.entity_starts
        for i, player in enumerate(entity_starts):
            if player.type != "player":
                continue

            players_matchmake.append(player.name)
        
        return await render_template(
            request, "game/laserball.html",
            game=game, get_entity_end=get_entity_end, get_laserballstats=get_laserballstats,
            fire_score=await game.get_red_score(),
            ice_score=await game.get_blue_score(),
            score_chart_labels=[{"x": t, "y": await game.get_rounds_at_time(t*60*1000)} for t in arange(0, 900000//1000//60+0.5, 0.5)],
            score_chart_data_red=[await game.get_red_score_at_time(t) for t in range(0, 900000+30000, 30000)],
            score_chart_data_blue=[await game.get_blue_score_at_time(t) for t in range(0, 900000+30000, 30000)],
            score_chart_data_rounds=[await game.get_rounds_at_time(t) for t in range(0, 900000+30000, 30000)],
            win_chance_after_game=await game.get_win_chance_after_game(),
            game_end_time_decimal=min(math.ceil((await game.scores.order_by("-time").first()).time/1000/60*2)/2, 15),
            players_matchmake=players_matchmake,
            is_admin=is_admin(request)
        )
    else:
        raise exceptions.NotFound("Not found: Invalid game type")