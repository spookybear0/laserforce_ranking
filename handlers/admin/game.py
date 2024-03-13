from sanic import Request
from shared import app
from utils import render_template, admin_only
from typing import Union, Optional
from db.sm5 import SM5Game, SM5Stats
from db.laserball import LaserballGame, LaserballStats
from db.game import EntityEnds
from sanic import exceptions, response
from helpers import ratinghelper, adminhelper
from sanic.log import logger
import os

async def get_entity_end(entity) -> Optional[EntityEnds]:
    return await EntityEnds.filter(entity=entity).first()

async def get_sm5stats(entity) -> Optional[SM5Stats]:
    return await SM5Stats.filter(entity=entity).first()

async def get_laserballstats(entity) -> Optional[LaserballStats]:
    return await LaserballStats.filter(entity=entity).first()

@app.get("/admin/game/<mode>/<id>")
@admin_only
async def admin_game(request: Request, mode: str, id: Union[int, str]) -> str:
    if mode == "sm5":
        game: SM5Game = await SM5Game.filter(id=id).prefetch_related("entity_starts").first()

        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")

        return await render_template(
            request, "admin/game/sm5.html",
            game=game, get_entity_end=get_entity_end,
            get_sm5stats=get_sm5stats, fire_score=await game.get_red_score(),
            earth_score=await game.get_green_score(),
            battlesuits=await game.get_battlesuits(),
            players=await game.get_players(),
            previous_game_id=await game.get_previous_game_id(),
            next_game_id=await game.get_next_game_id(),
        )
    elif mode == "laserball":
        game = await LaserballGame.filter(id=id).prefetch_related("entity_starts").first()

        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")
        
        return await render_template(
            request, "admin/game/laserball.html",
            game=game, get_entity_end=get_entity_end,
            get_laserballstats=get_laserballstats,
            players=await game.get_players(),
            battlesuits=await game.get_battlesuits(),
            fire_score=await game.get_red_score(),
            ice_score=await game.get_blue_score()
        )
    else:
        raise exceptions.NotFound("Not found: Invalid game type")
    
@app.post("/admin/game/<mode>/<id>/rank")
@admin_only
async def admin_game_rank(request: Request, mode: str, id: Union[int, str]) -> str:
    if mode == "sm5":
        game = await SM5Game.filter(id=id).first()
    elif mode == "laserball":
        game = await LaserballGame.filter(id=id).first()
    else:
        raise exceptions.NotFound("Not found: Invalid game type")
    
    game.ranked = True
    await game.save()

    await ratinghelper.update_sm5_ratings(game)

    return response.json({"status": "ok"})

@app.post("/admin/game/<mode>/<id>/unrank")
@admin_only
async def admin_game_unrank(request: Request, mode: str, id: Union[int, str]) -> str:
    if mode == "sm5":
        game = await SM5Game.filter(id=id).first()
    elif mode == "laserball":
        game = await LaserballGame.filter(id=id).first()
    else:
        raise exceptions.NotFound("Not found: Invalid game type")
    
    game.ranked = False
    await game.save()

    return response.json({"status": "ok"})

@app.post("/admin/game/<mode>/<id>/log_in_player")
@admin_only
async def admin_game_log_in_player(request: Request, mode: str, id: Union[int, str]) -> str:
    if mode == "sm5":
        game = await SM5Game.filter(id=id).first()
    elif mode == "laserball":
        game = await LaserballGame.filter(id=id).first()
    else:
        raise exceptions.NotFound("Not found: Invalid game type")
    
    logger.debug("Logging in player")
    
    battlesuit = request.json.get("battlesuit")
    codename = request.json.get("codename")

    await adminhelper.manually_login_player_sm5(game, battlesuit, codename, mode)

    return response.json({"status": "ok"})

@app.post("/admin/game/<mode>/<id>/delete")
@admin_only
async def admin_game_delete(request: Request, mode: str, id: Union[int, str]) -> str:
    if mode == "sm5":
        game = await SM5Game.filter(id=id).first()
        await game.delete()
        os.remove("sm5_tdf/" + game.tdf_name)
    elif mode == "laserball":
        game = await LaserballGame.filter(id=id).first()
        await game.delete()
        os.remove("laserball_tdf/" + game.tdf_name)
    else:
        raise exceptions.NotFound("Not found: Invalid game type")
    
    return response.json({"status": "ok"})

@app.post("/admin/game/<mode>/<id>/delete_player")
@admin_only
async def admin_game_delete_player(request: Request, mode: str, id: Union[int, str]) -> str:
    if mode == "sm5":
        game = await SM5Game.filter(id=id).first()
    elif mode == "laserball":
        game = await LaserballGame.filter(id=id).first()
    else:
        raise exceptions.NotFound("Not found: Invalid game type")
    
    logger.debug("Deleting player from game")
    
    info = request.json.get("player_info")

    codename = info.split("|")[0]
    id = info.split("|")[1]

    await adminhelper.delete_player_from_game(game, codename, id, mode)

    return response.json({"status": "ok"})