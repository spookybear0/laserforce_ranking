import os
import sys
import router
import asyncio
from aiohttp import web
from config import config
from mysql import MySQLPool
from shared import sql, app
from helpers.userhelper import player_cron

path = os.path.dirname(os.path.abspath(__file__))
os.chdir(path)

async def async_main():
    global sql
    sql = await MySQLPool.connect_with_config()

def main():
    try:
        asyncio.get_event_loop()
    except (RuntimeError, DeprecationWarning):
        asyncio.set_event_loop(asyncio.new_event_loop())
        
    loop = asyncio.get_event_loop()
    
    loop.run_until_complete(async_main())
    
    app.router.add_static("/assets/", path="./assets/", name="assets")
    router.add_all_routes(app)
    web.run_app(app, host="localhost", port=8000)
    
if __name__ == "__main__":
    main()