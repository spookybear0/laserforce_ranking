from sanic import Request
from shared import app
from utils import render_template
from db.models import SM5Game, EntityEnds, EntityStarts, SM5Stats, LaserballGame, LaserballStats
from sanic import exceptions, response
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

@app.get("/game/<type:str>/<id:int>/scorecard/<entity_end_id:int>")
@sentry_trace
async def scorecard(request: Request, type: str, id: int, entity_end_id: int) -> str:
    if type == "sm5":
        game = await SM5Game.filter(id=id).first()

        if not game:
            raise exceptions.NotFound("Game not found")
        
        entity_end = await EntityEnds.filter(id=entity_end_id).first()

        if not entity_end:
            raise exceptions.NotFound("Scorecard not found")
        
        entity_start = await entity_end.entity
        

        return await render_template(
            request,
            "game/scorecard_sm5.html",
            game=game,
            entity_start=entity_start,
            entity_end=entity_end,
        )
        
    return response.HTTPResponse("Not implemented yet")