import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
os.chdir(path)
sys.path.append(path)

from mysql import MySQLPool
import jinja2
from sanic import Sanic
from sanic_jinja2 import SanicJinja2
from sanic_session import Session, AIORedisSessionInterface
from config import config
from sanic_cors import CORS
import aioredis

# we need to set up our app before we import anything else

app = Sanic("laserforce_rankings")
app.config.USE_UVLOOP = False

CORS(app, resources={r"/api/*": {"origins": "*"}})
session = Session()
app.ctx.redis = aioredis.from_url(config["redis"], decode_responses=True)
session.init_app(app, interface=AIORedisSessionInterface(app.ctx.redis))

app.ctx.jinja = SanicJinja2(
    app,
    loader=jinja2.FileSystemLoader("./assets/html"),
    pkg_path="assets/html",
    extensions=["jinja2.ext.loopcontrols"],
    enable_async=True
)
app.ctx.sql = MySQLPool()
app.ctx.config = config

import asyncio
import router
from mysql import MySQLPool
from tortoise import Tortoise
from config import config
from helpers import cachehelper

TORTOISE_ORM = {
    "connections": { "default": f"mysql://{config['db_user']}:{config['db_password']}@{config['db_host']}:{config['db_port']}/laserforce" },
    "apps": {
        "models": {
            "models": ["db.game", "db.laserball", "db.legacy", "db.player", "db.sm5", "aerich.models"],
            "default_connection": "default"
        }
    }
}

@app.exception(AttributeError)
async def handle_attribute_error(request, exception):
    # check if the error is due to _sentry_hub
    if "_sentry_hub" not in str(exception):
        raise exception

@app.listener("before_server_stop")
async def close_db(app, loop) -> None:
    """
    Close the database connection when the server stops.
    """
    await app.ctx.sql.close()
    await Tortoise.close_connections()

@app.signal("server.init.before")
async def setup_app(app, loop) -> None:
    """
    Start the server in a production environment.
    """
    app.ctx.sql = await MySQLPool.connect_with_config()

    await Tortoise.init(
        config=TORTOISE_ORM
    )

    # use cache on production server
    cachehelper.use_cache()

async def main() -> None:
    """
    Start the server in a development/nonprod environment.
    """
    app.ctx.sql = await MySQLPool.connect_with_config()

    await Tortoise.init(
        config=TORTOISE_ORM
    )

    #await adminhelper.repopulate_database()

    # no cache on dev server

    server = await app.create_server(host="localhost", port=8000, debug=True, return_asyncio_server=True)

    await server.startup()
    await server.after_start()
    await server.serve_forever()

router.add_all_routes(app)
app.static("assets", "assets", name="assets")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Exiting...")