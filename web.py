import os
import sys
import router
import shared
import asyncio
from aiohttp import web
from config import config
from mysql import MySQLPool
from helpers.userhelper import player_cron

path = os.path.dirname(os.path.abspath(__file__))
os.chdir(path)

async def async_main():
    shared.sql = await MySQLPool.connect(config["db_host"], config["db_user"], config["db_password"], config["db_database"], config["db_port"])

def main():
    try:
        asyncio.get_event_loop()
    except (RuntimeError, DeprecationWarning):
        asyncio.set_event_loop(asyncio.new_event_loop())
        
    loop = asyncio.get_event_loop()
    
    loop.run_until_complete(async_main())
    
    shared.app.router.add_static("/assets/", path="./assets/", name="assets")
    router.add_all_routes(shared.app)
    web.run_app(shared.app, host="localhost", port=8000, loop=loop)
    
if __name__ == "__main__":
    main()