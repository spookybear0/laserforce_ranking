from tortoise import Tortoise
from config import config
from db.migrations import migrate_from_sql
from helpers import tdfhelper, userhelper
from db.models import Player, Permission

async def repopulate_database() -> None:
    await Tortoise.generate_schemas()

    await migrate_from_sql(False)

    # some fixes

    await Player.filter(codename="ëMîlÿ").update(ipl_id="#RFSjNZ")
    await Player.filter(codename="Survivor").update(permissions=Permission.ADMIN, password=userhelper.hash_password(config["root_password"]))

    await Player.all().update(sm5_mu=25, sm5_sigma=25/3)

    await tdfhelper.parse_all_tdfs()