import os
import sys
import asyncio
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
    server = await app.create_server(host="localhost", port=8000, return_asyncio_server=True)

    await server.startup()
    await server.serve_forever()
    
if __name__ == "__main__":
    asyncio.set_event_loop(asyncio.new_event_loop())
    asyncio.run(main())