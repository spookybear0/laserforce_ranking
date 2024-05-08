from typing import Union

from sanic.log import logger
from tortoise import Tortoise

from config import config
from db.laserball import LaserballGame
from db.player import Player
from db.sm5 import SM5Stats, SM5Game
from db.types import Permission
from helpers import tdfhelper, userhelper, ratinghelper
from shared import app


async def repopulate_database() -> None:
    await Tortoise.generate_schemas()

    sql = app.ctx.sql

    # get all old player_id's

    ids = await sql.fetchall("SELECT codename, player_id FROM players")

    for codename, player_id in ids:
        await Player.filter(codename=codename).update(player_id=player_id)

    # some fixes

    await Player.filter(codename="ëMîlÿ").update(entity_id="#RFSjNZ")
    await Player.filter(codename="Survivor").update(permissions=Permission.ADMIN,
                                                    password=userhelper.hash_password(config["root_password"]))

    await Player.all().update(sm5_mu=ratinghelper.MU, sm5_sigma=ratinghelper.SIGMA, laserball_mu=ratinghelper.MU,
                              laserball_sigma=ratinghelper.SIGMA)

    await tdfhelper.parse_all_tdfs()


async def manually_login_player_sm5(game: Union[SM5Game, LaserballGame], battlesuit: str, codename: str,
                                    mode: str) -> None:
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
    elif mode == "laserball":
        tdf = "laserball_tdf/" + tdf
    else:
        raise ValueError("Invalid mode")

    # simple find and replace

    with open(tdf, "r", encoding="utf-16") as f:
        contents = f.read()

        contents = contents.replace(old_entity_id, player.entity_id)
        contents = contents.replace(battlesuit, codename)

    with open(tdf, "w", encoding="utf-16") as f:
        f.write(contents)

    logger.debug("Wrote to file successfully")


async def delete_player_from_game(game: Union[SM5Game, LaserballGame], codename: str, id: int, mode: str) -> None:
    """
    Delete a player from a game

    Usually for when a player exits the arena and
    the game creates a new entity for them
    after they walk through the door
    """

    try:
        logger.debug(f"Deleting player {codename}")
        entity_start = await game.entity_starts.filter(name=codename, id=id).first()

        logger.debug(f"Deleting entity start {entity_start.name}")

        try:
            await entity_start.delete()
        except Exception:
            logger.warning("Failed to delete entity start, continuing")
    except Exception:
        logger.warning("Failed to delete entity start, continuing")

    try:
        logger.debug("Deleting entity end")
        try:
            await (await entity_start.get_entity_end()).delete()
        except Exception:
            logger.warning("Failed to delete entity end, continuing")
    except Exception:
        logger.warning("Failed to delete entity end, continuing")

    logger.debug("Deleting events")

    # go through all events and delete them

    if entity_start is None:
        return

    async for event in game.events:
        arguments = event.arguments
        for info in arguments:
            if entity_start.entity_id in info:
                await event.delete()

    if mode == "sm5":
        # delete sm5stats

        logger.debug("Deleting sm5stats")

        sm5_stats = (await SM5Stats.filter(entity__entity_id=entity_start.entity_id).first())
        try:
            await SM5Stats.filter(id=sm5_stats.id).delete()
        except Exception:
            logger.warning("Failed to delete sm5stats, continuing")
    elif mode == "laserball":
        # delete laserballstats

        logger.debug("Deleting laserballstats")

        sm5_stats = (await LaserballGame.filter(entity__entity_id=entity_start.entity_id).first())
        try:
            await LaserballGame.filter(id=sm5_stats.id).delete()
        except Exception:
            logger.warning("Failed to delete laserballstats, continuing")
    else:
        raise ValueError("Invalid mode")

    logger.debug("Deleting data on the tdf file")

    # update the tdf file

    tdf = game.tdf_name

    if mode == "sm5":
        tdf = "sm5_tdf/" + tdf
    elif mode == "laserball":
        tdf = "laserball_tdf/" + tdf
    else:
        raise ValueError("Invalid mode")

    # simple find and replace

    with open(tdf, "r", encoding="utf-16") as f:
        contents = f.read()

        contents = contents.replace(entity_start.entity_id, "")
        contents = contents.replace(codename, "")

    with open(tdf, "w", encoding="utf-16") as f:
        f.write(contents)

    logger.debug("Wrote to file successfully")
