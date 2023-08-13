import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
os.chdir(path)
sys.path.append(path)

import asyncio
import router
from mysql import MySQLPool
from shared import app
import sanic
from tortoise import Tortoise
from config import config
from db.migrations import migrate_from_sql
from helpers import tdfhelper, ratinghelper
from db.models import SM5Game, Player

async def repopulate_database() -> None:
    await Tortoise.generate_schemas()
    await migrate_from_sql(True)

    await Player.all().update(sm5_mu=25, sm5_sigma=25/3)

    await tdfhelper.parse_all_tdfs()


async def main() -> None:
    router.add_all_routes(app)
    app.static("assets", "assets", name="assets")

    app.ctx.sql = await MySQLPool.connect_with_config()

    await Tortoise.init(
        db_url=f"mysql://{config['db_user']}:{config['db_password']}@{config['db_host']}:{config['db_port']}/laserforce",
        modules={"models": ["db.models"]}
    )

    await repopulate_database()

    debug = False
    if "--debug" in sys.argv or "--dev" in sys.argv:
        debug = True

    server = await app.create_server(host="localhost", port=8000, debug=debug, return_asyncio_server=True)

    await server.startup()
    await server.after_start()
    await server.serve_forever()
    
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Exiting...")