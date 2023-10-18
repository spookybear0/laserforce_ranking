from tortoise import Tortoise
from config import config
from db.migrations import migrate_from_sql
from helpers import tdfhelper, userhelper
from db.models import Player, Permission, SM5Game, EntityEnds, EntityStarts, Events
from typing import List

async def repopulate_database() -> None:
    await Tortoise.generate_schemas()

    await migrate_from_sql(False)

    # some fixes

    await Player.filter(codename="ëMîlÿ").update(ipl_id="#RFSjNZ")
    await Player.filter(codename="Survivor").update(permissions=Permission.ADMIN, password=userhelper.hash_password(config["root_password"]))

    await Player.all().update(sm5_mu=25, sm5_sigma=25/3)

    await tdfhelper.parse_all_tdfs()

async def reload_database() -> None:
    """
    CAUTION

    this function will delete the entire database and create it again

    could potentially lose all data, back up beforehand
    """
    
    # TODO: implement this with an automatic backup
    pass

async def manually_login_player_sm5(game: SM5Game, prev_codename: str, player: Player) -> bool:
    """
    Manually log in a player

    This is used when a player logs in with a different codename than the one they registered with.
    For instance, using a normal pack and not logging in (therefore being a different codename)

    If we know their codename we can log in for them
    """

    # TODO: build interface on front end
    
    if player.codename == prev_codename:
        return False
    
    entity: EntityStarts = await game.get_entity_start_from_name(prev_codename)

    if entity is None:
        return False
    
    eid = entity.entity_id

    # get the tdf for the game

    tdf_filename = game.tdf_name

    f = open(f"sm5_tdf/{tdf_filename}", "r") # test this

    data = f.read()

    f.close()

    newdata = data.replace(eid, player.ipl_id)

    f = open(f"sm5_tdf/{tdf_filename}", "w")
    f.write(newdata)
    f.close()

    # update the database

    await game.entity_starts.filter(entity_id=eid).update(entity_id=player.ipl_id)
    await game.entity_ends.filter(entity__entity_id=eid).update(entity__entity_id=player.ipl_id)

    # look at arguments and replace old pack with new one
    events: List[Events] = await game.events.filter(args__contains=eid).all()

    for event in events:
        event.arguments[event.arguments.index(eid)] = player.ipl_id
        await event.save()

    return True