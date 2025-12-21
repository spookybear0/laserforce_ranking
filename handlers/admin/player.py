from typing import Union

from sanic import Request, response, exceptions

from db.player import Player
from db.tag import Tag, TagType
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
        player = await Player.get_or_none(codename=id)  # could be codename
        if not player:
            return response.json({"status": "error", "message": "Player not found"}, status=404)

    tag = request.json.get("tag")
    tag_type = request.json.get("type", "HF").upper()

    logger.info(f"Adding tag {tag} of type {tag_type} to player {player}")

    try:
        tag_type = TagType(tag_type)
    except ValueError:
        logger.error(f"Invalid tag type: {tag_type}")
        return response.json({"status": "error", "message": "Invalid tag type"}, status=400)

    logger.info(f"Adding tag {tag} to player {player}")

    if tag:
        existing_tag = await Tag.get_or_none(id=tag)
        if existing_tag:
            logger.info(f"Tag {tag} already exists for player {player}")
            return response.json({"status": "error", "message": "Tag already exists"}, status=400)
        
        new_tag = Tag(id=tag, type=tag_type, player=player)
        await new_tag.save()

        return response.json({"status": "ok"})
    
    return response.json({"status": "error"}, status=400)