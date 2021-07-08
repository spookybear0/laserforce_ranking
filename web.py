from helpers import ranking_cron, log_game # type: ignore
from aiohttp import web
from async_cron.job import CronJob # type: ignore
from async_cron.schedule import Scheduler # type: ignore
import multiprocessing as mp
import asyncio
import aiohttp_jinja2
import jinja2
import os

app = web.Application()
routes = web.RouteTableDef()

os.chdir(os.path.dirname(os.path.realpath(__file__)))
templates = aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader("html"))

msh = Scheduler()
cron = CronJob(name="ranking").every(1).hour.go(ranking_cron)
msh.add_job(cron)

async def render_template(r, template, *args, **kwargs) -> web.Response:
    text = templates.get_template(template).render(*args, **kwargs)
    return web.Response(text=text, content_type="text/html")

@routes.get("/log")
async def log_game(r: web.RequestHandler):
    return await render_template(r, "log.html")

@routes.post("/log")
async def log_game(r: web.RequestHandler):
    data = await r.post()
    
    id = data["id"]
    role = data["role"]
    won = data["won"]
    
    try:
        score = int(data["score"])
    except:
        return web.Response(text="401: Error, invalid data!")
    
    if won == "on":
        won = True
    else:
        won = False
    
    if not role in ["scout", "heavy", "comamnder", "medic", "ammo"] or len(id.split("-")) != 3:
        return web.Response(text="401: Error, invalid data!")
    try:
        await log_game(id, won, role, score)
    except:
        return web.Response(text="500: Error, game was not logged!")
    else:
        return web.Response(text="200: Logged!")

def start_cron():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(msh.start())

if __name__ == "__main__":
    mp.set_start_method("spawn")
    cronprocess = mp.Process(target=start_cron)
    cronprocess.start()
    app.router.add_routes(routes)
    web.run_app(app)