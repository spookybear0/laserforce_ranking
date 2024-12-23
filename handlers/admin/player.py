from typing import Union

from sanic import Request, response, exceptions

from db.player import Player
from shared import app
from utils import render_template, admin_only
from sanic.log import logger


@app.get("/admin/player/<id>")
@admin_only
async def admin_player(request: Request, id: Union[int, str]) -> str:
    player = await Player.get_or_none(player_id=id)

    if not player:
        try:
            player = await Player.filter(codename=id).first()  # could be codename
        except Exception:
            raise exceptions.NotFound("Not found: Invalid ID or codename")

    return await render_template(request,
                                 "admin/player.html",
                                 player=player,
                                 )

@app.post("/admin/player/<id>/add_tag")
@admin_only
async def admin_player_add_tag(request: Request, id: Union[int, str]) -> str:
    player = await Player.get_or_none(player_id=id)

    if not player:
        try:
            player = await Player.filter(codename=id).first()  # could be codename
        except Exception:
            raise exceptions.NotFound("Not found: Invalid ID or codename")

    tag = request.json.get("tag")

    logger.info(f"Adding tag {tag} to player {player}")

    if tag:
        if tag in player.rfid_tags:
            logger.info(f"Tag {tag} already exists in player {player}")
            return response.json({"status": "already_exists"})
        player.rfid_tags.append(tag)
        await player.save()
        return response.json({"status": "ok"})
    
    return response.json({"status": "error"}, status=400)