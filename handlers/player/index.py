from helpers.userhelper import get_median_role_score
from objects import GameType, Team
from utils import render_template, get_post
from helpers import gamehelper
from shared import app
from sanic import Request, HTTPResponse, response, exceptions
from shared import app
from urllib.parse import unquote
from typing import Union
from db.models import Player, SM5Game
from helpers.statshelper import sentry_trace

sql = app.ctx.sql

async def get_entity_start(game, player):
    return await game.entity_starts.filter(entity_id=player.ipl_id).first()

async def get_entity_end(game, entity_start):
    return await game.entity_ends.filter(entity=entity_start.id).first()

async def get_sm5_stat(game, entity_start):
    return await game.sm5_stats.filter(entity_id=entity_start.id).first()

@app.get("/player/<id>")
@sentry_trace
async def player_get(request: Request, id: Union[int, str]):
    id = unquote(id)

    player = await Player.get_or_none(player_id=id)

    if not player:
        try:
            player = await Player.filter(codename=id).first() # could be codename
        except Exception:
            raise exceptions.NotFound("Not found: Invalid ID or codename")
        
    recent_games = SM5Game.filter(entity_starts__entity_id=player.ipl_id).order_by("-start_time").limit(10)
    
    return await render_template(request, "player/player.html",
                                # general player info
                                player=player,
                                recent_games=recent_games,
                                get_entity_start=get_entity_start,
                                get_entity_end=get_entity_end,
                                get_sm5_stat=get_sm5_stat,
                                )

@app.post("/player")
async def player_post(request: Request):
    data = get_post(request)
    user = data["userid"]
    return response.redirect(f"/player/{user}")