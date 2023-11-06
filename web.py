import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
os.chdir(path)
sys.path.append(path)

if sys.platform != "win32":
    import asyncio
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    uvloop.install()

from mysql import MySQLPool
import jinja2
from sanic import Sanic
from sanic_jinja2 import SanicJinja2
from sanic_session import Session, InMemorySessionInterface
from config import config
from sanic_cors import CORS

# we need to set up our app before we import anything else

app = Sanic("laserforce_rankings")

CORS(app, resources={r"/api/*": {"origins": "*"}})
Session(app, interface=InMemorySessionInterface())

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
from helpers import cachehelper, adminhelper

@app.signal("server.init.before")
async def setup_app(app, loop) -> None:
    """
    Start the server in a production environment.
    """
    app.ctx.sql = await MySQLPool.connect_with_config()

    await Tortoise.init(
        db_url=f"mysql://{config['db_user']}:{config['db_password']}@{config['db_host']}:{config['db_port']}/laserforce",
        modules={"models": ["db.models"]}
    )

    # use cache on production server
    cachehelper.use_cache()

async def main() -> None:
    """
    Start the server in a development/nonprod environment.
    """
    app.ctx.sql = await MySQLPool.connect_with_config()

    await Tortoise.init(
        db_url=f"mysql://{config['db_user']}:{config['db_password']}@{config['db_host']}:{config['db_port']}/laserforce",
        modules={"models": ["db.models"]}
    )

    #await adminhelper.repopulate_database()

    cachehelper.use_cache()

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