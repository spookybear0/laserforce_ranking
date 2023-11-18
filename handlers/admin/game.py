from sanic import Request
from shared import app
from utils import render_template, admin_only
from typing import Union, List
from db.models import Player, SM5Game, EntityEnds, EntityStarts, SM5Stats, LaserballGame, LaserballStats
from sanic import exceptions, response

async def get_entity_end(entity):
    return await EntityEnds.filter(entity=entity).first()

async def get_sm5stats(entity):
    return await SM5Stats.filter(entity=entity).first()

async def get_laserballstats(entity):
    return await LaserballStats.filter(entity=entity).first()

@app.get("/admin/game/<mode>/<id>")
@admin_only
async def admin_game(request: Request, mode: str, id: Union[int, str]):
    if mode == "sm5":
        game: SM5Game = await SM5Game.filter(id=id).prefetch_related("entity_starts").first()

        players_matchmake = []
        entity_starts: List[EntityStarts] = game.entity_starts
        for i, player in enumerate(entity_starts):
            if player.type != "player":
                continue

            players_matchmake.append(player.name)

        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")
        return await render_template(
            request, "admin/game/sm5.html",
            game=game, get_entity_end=get_entity_end,
            get_sm5stats=get_sm5stats, fire_score=await game.get_red_score(),
            earth_score=await game.get_green_score(),
            battlesuits=await game.get_battlesuits(),
        )
    elif mode == "lb":
        game = await LaserballGame.filter(id=id).prefetch_related("entity_starts").first()

        players_matchmake = []
        entity_starts: List[EntityStarts] = game.entity_starts
        for i, player in enumerate(entity_starts):
            if player.type != "player":
                continue

            players_matchmake.append(player.name)
        
        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")
        return await render_template(
            request, "admin/game/laserball.html",
            game=game, get_entity_end=get_entity_end, get_laserballstats=get_laserballstats,
            fire_score=await game.get_red_score(),
            ice_score=await game.get_blue_score()
        )
    else:
        raise exceptions.NotFound("Not found: Invalid game type")
    
@app.post("/admin/game/<mode>/<id>/rank")
@admin_only
async def admin_game_rank(request: Request, mode: str, id: Union[int, str]):
    if mode == "sm5":
        game = await SM5Game.filter(id=id).first()
    elif mode == "lb":
        game = await LaserballGame.filter(id=id).first()
    else:
        raise exceptions.NotFound("Not found: Invalid game type")
    
    game.ranked = True
    await game.save()

    return response.json({"status": "ok"})

@app.post("/admin/game/<mode>/<id>/unrank")
@admin_only
async def admin_game_unrank(request: Request, mode: str, id: Union[int, str]):
    if mode == "sm5":
        game = await SM5Game.filter(id=id).first()
    elif mode == "lb":
        game = await LaserballGame.filter(id=id).first()
    else:
        raise exceptions.NotFound("Not found: Invalid game type")
    
    game.ranked = False
    await game.save()

    return response.json({"status": "ok"})

@app.post("/admin/game/<mode>/<id>/log_in_player")
@admin_only
async def admin_game_log_in_player(request: Request, mode: str, id: Union[int, str]):
    if mode == "sm5":
        game = await SM5Game.filter(id=id).first()
    elif mode == "lb":
        game = await LaserballGame.filter(id=id).first()
    else:
        raise exceptions.NotFound("Not found: Invalid game type")
    
    battlesuit = request.args.get("battlesuit")
    codename = request.args.get("codename")

    player = await Player.filter(name=codename).first()
    
    entity_start = await game.entity_starts.filter(name=battlesuit, battlesuit=battlesuit).first()

    old_entity_id = entity_start.entity_id

    entity_start.name = codename
    entity_start.entity_id = player.ipl_id

    await entity_start.save()

    # go through all events and change @number to #entity_id

    async for event in game.events:
        data = event.data
        for info in data:
            if info == old_entity_id:
                data[data.index(info)] = player.ipl_id
        event.data = data
        await event.save()

    # update the tdf file

    tdf = game.tdf_name

    if mode == "sm5":
        tdf = "sm5_tdf/" + tdf
    elif mode == "lb":
        tdf = "lb_tdf/" + tdf

    # simple find and replace

    with open(tdf, "r") as f:
        contents = f.read()

        contents = contents.replace(old_entity_id, codename)

    with open(tdf, "w") as f:
        f.write(contents)

    return response.json({"status": "ok"})