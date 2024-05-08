import asyncio
import os
import sys
import threading

import webview
from sanic.server.async_server import AsyncioServer

import router
from mysql import MySQLPool
from shared import app

path = os.path.dirname(os.path.abspath(__file__))
os.chdir(path)
sys.path.append(path)


async def main():
    router.add_all_routes(app)
    app.static("assets", "assets", name="assets")

    app.ctx.sql = await MySQLPool.connect_with_config()
    server: AsyncioServer = await app.create_server(host="localhost", port=8000, return_asyncio_server=True)

    await server.startup()
    await server.serve_forever()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    threading.Thread(target=lambda: loop.run_until_complete(main()), daemon=True).start()

    webview.create_window("Test", "http://localhost:8000/")
    webview.start(http_server=True)
