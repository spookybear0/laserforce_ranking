import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
os.chdir(path)
sys.path.append(path)

import jinja2
from sanic import Sanic, log, exceptions
from sanic_jinja2 import SanicJinja2
from sanic_session import Session, AIORedisSessionInterface, InMemorySessionInterface
from config import config
from sanic_cors import CORS
import aioredis
from tailwind import generate_tailwind_css
from sanic.log import logger
from handlers.api import api_bp
from sanic_ext import openapi

# we need to set up our app before we import anything else

app = Sanic("laserforce_rankings")

app.ext.openapi.describe(
    "Laserforce Rankings API",
    version="1.0.0",
    description="This is the API for the Laserforce Rankings website. It provides access to game data, player data, and more.",
)

CORS(app, resources={r"/api/*": {"origins": "*"}})
session = Session()
if config["redis"] not in ["", None, False]:
    app.ctx.redis = aioredis.from_url(config["redis"], decode_responses=True)
    interface = AIORedisSessionInterface(app.ctx.redis)
else:
    interface = InMemorySessionInterface()
session.init_app(app, interface=interface)

app.ctx.jinja = SanicJinja2(
    app,
    loader=jinja2.FileSystemLoader("./assets/html"),
    pkg_path="assets/html",
    extensions=["jinja2.ext.loopcontrols"],
    enable_async=True
)
app.ctx.config = config

import asyncio
import router
from tortoise import Tortoise
from config import config
from helpers import cachehelper
import utils

TORTOISE_ORM = {
    "connections": {
        "default": f"mysql://{config['db_user']}:{config['db_password']}@{config['db_host']}:{config['db_port']}/{config['db_name']}",
    },
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
    if "_sentry_hub" not in str(exception) or "sentry_sdk" not in str(exception):
        raise exception

@app.exception(exceptions.RequestCancelled, asyncio.exceptions.CancelledError)
async def handle_request_cancelled(request, exception):
    """
    Handle request cancelled exceptions.
    This is a no-op to prevent logging these exceptions.
    """
    pass

@app.listener("before_server_stop")
async def close_db(app, loop) -> None:
    """
    Close the database connection when the server stops.
    """
    await Tortoise.close_connections()


@app.signal("server.init.before")
async def setup_app(app, loop) -> None:
    """
    Start the server in a production environment.
    """
    app.ctx.banner = {"text": None, "type": None}
    app.ctx.banner_type_to_color = utils.banner_type_to_color

    await Tortoise.init(
        config=TORTOISE_ORM
    )

    # use cache on production server

    # check for --debug argument
    if "--debug" not in sys.argv:
        logger.info("Using cache")
        cachehelper.use_cache()
        await cachehelper.precache_all_functions()
    else:
        logger.info("Not using cache, --debug argument detected")

    # generate css needed for the site
    generate_tailwind_css()


async def main() -> None:
    """
    Start the server in a development/nonprod environment.
    """
    app.ctx.banner = {"text": "", "type": None}
    app.ctx.banner_type_to_color = utils.banner_type_to_color

    await Tortoise.init(
        config=TORTOISE_ORM
    )

    # generate css needed for the site
    generate_tailwind_css()

    # no cache on dev server

    server = await app.create_server(host="localhost", port=8000, debug=True, return_asyncio_server=True)

    await server.startup()
    await server.after_start()
    await server.serve_forever()

# api blueprint

app.blueprint(api_bp)

# add routes

router.add_all_routes(app)

# exclude routes from documentation unless part of the API blueprint

# go through every route and replace it with route = openapi.exclude()(route), then save it back to app.router.routes

for route in app.router.routes:
    if "api." not in route.name:
        route.handler = openapi.exclude()(route.handler)

# static files

app.static("assets", "assets", name="assets")


def filter(record):
    # don't allow anything with "Dispatching singal" or "Sanic-CORS"
    if "Dispatching signal" in record.getMessage() or "Sanic-CORS" in record.getMessage():
        return False
    return True

log.logger.addFilter(filter)

if __name__ == "__main__":
    if os.name == "nt":
        loop = asyncio.new_event_loop()
    else:
        try:
            import uvloop
        except ImportError:
            loop = asyncio.new_event_loop()
        loop = uvloop.new_event_loop()

    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Exiting...")
else:
    if os.name == "nt":
        app.config.USE_UVLOOP = False
    else:
        app.config.USE_UVLOOP = True
        try:
            import uvloop
        except ImportError:
            app.config.USE_UVLOOP = False