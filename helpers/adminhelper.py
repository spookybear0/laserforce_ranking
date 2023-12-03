from tortoise import Tortoise
from config import config
from helpers import tdfhelper, userhelper, ratinghelper
from db.models import Player, Permission, SM5Game, EntityStarts, Events
from typing import List
from sanic.log import logger

async def repopulate_database() -> None:
    await Tortoise.generate_schemas()

    # some fixes

    await Player.filter(codename="ëMîlÿ").update(entity_id="#RFSjNZ")
    await Player.filter(codename="Survivor").update(permissions=Permission.ADMIN, password=userhelper.hash_password(config["root_password"]))

    await Player.all().update(sm5_mu=ratinghelper.MU, sm5_sigma=ratinghelper.SIGMA, laserball_mu=ratinghelper.MU, laserball_sigma=ratinghelper.SIGMA)

    await tdfhelper.parse_all_tdfs()

async def manually_login_player_sm5(game: SM5Game, battlesuit: str, codename: str) -> bool:
    """
    Manually log in a player

    This is used when a player logs in with a different codename than the one they registered with.
    For instance, using a normal pack and not logging in (therefore being a different codename)

    If we know their codename we can log in for them
    """

    logger.debug(f"Logging in player {battlesuit} as {codename}")

    player = await Player.filter(codename=codename).first()
    
    entity_start = await game.entity_starts.filter(name=battlesuit).first()

    old_entity_id = entity_start.entity_id

    entity_start.name = codename
    entity_start.entity_id = player.entity_id

    logger.debug(f"Changing entity ID from {old_entity_id} to {player.entity_id}")

    await entity_start.save()

    logger.debug("Changing events entity_id")

    # go through all events and change @number to #entity_id

    async for event in game.events:
        arguments = event.arguments
        for info in arguments:
            if info == old_entity_id:
                arguments[arguments.index(info)] = player.entity_id
        event.arguments = arguments
        await event.save()

    logger.debug("Changing data on the tdf file")

    # update the tdf file

    tdf = game.tdf_name

    if mode == "sm5":
        tdf = "sm5_tdf/" + tdf
    elif mode == "lb":
        tdf = "laserball_tdf/" + tdf

    # simple find and replace

    with open(tdf, "r", encoding="utf-16") as f:
        contents = f.read()

        contents = contents.replace(old_entity_id, player.entity_id)
        contents = contents.replace(battlesuit, codename)

    with open(tdf, "w", encoding="utf-16") as f:
        f.write(contents)

    logger.debug("Wrote to file successfully")