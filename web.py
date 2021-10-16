from helpers import ranking_cron, log_game, init_sql, player_cron, get_top_100 # type: ignore
from aiohttp import web
from objects import Role, Game, GamePlayer, Team
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
ranking = CronJob(name="ranking").every(1).hour.go(ranking_cron)
player = CronJob(name="player").every(1).hour.go(player_cron)
msh.add_job(ranking)
msh.add_job(player)

async def render_template(r, template, *args, **kwargs) -> web.Response:
    text = templates.get_template(template).render(*args, **kwargs)
    return web.Response(text=text, content_type="text/html")

@routes.get("/top")
async def top_get(r: web.RequestHandler):
    await init_sql()
    scout = await get_top_100(Role.SCOUT)
    heavy = await get_top_100(Role.HEAVY)
    ammo = await get_top_100(Role.AMMO)
    medic = await get_top_100(Role.MEDIC)
    commander = await get_top_100(Role.COMMANDER)
    return await render_template(r, "top.html", scout=scout, heavy=heavy, ammo=ammo, medic=medic, commander=commander)

@routes.get("/log")
async def log_game_get(r: web.RequestHandler):
    return await render_template(r, "log.html")

@routes.post("/log")
async def log_game_post(r: web.RequestHandler):
    await init_sql()
    data = await r.post()
    
    winner = data["winner"] # green or red
    red_players = []
    green_players = []
    
    for red_player in range(1, 8):
        try:
            player_id = data[f"rid{red_player}"]
            player_role = data[f"rrole{red_player}"]
            player_score = data[f"rscore{red_player}"]
        except KeyError:
            break
        game = GamePlayer(player_id, 0, Team.RED, Role(player_role), int(player_score))
        red_players.append(game)
    for green_player in range(1, 8):
        try:
            player_id = data[f"gid{green_player}"]
            player_role = data[f"grole{green_player}"]
            player_score = data[f"gscore{green_player}"]
        except KeyError:
            break
        game = GamePlayer(player_id, 0, Team.GREEN, Role(player_role), int(player_score))
        green_players.append(game)
        
    players = [*red_players, *green_players]
    
    try:
        score = int(data["score"])
    except:
        return web.Response(text="401: Error, invalid data! (score)")
    
    for player in players:
        if not player.role.value in ["scout", "heavy", "comamnder", "medic", "ammo"]:
            return web.Response(text="401: Error, invalid data! (role)")
        if len(player.player_id.split("-")) != 3:
            return web.Response(text="401: Error, invalid data! (id)")
            
    if not winner in ["green", "red"]:
        return web.Response(text="401: Error, invalid data! (team)")
    
    game = Game(0, winner, players=players) # game_id is 0 becaue its undefined
    
    try:
        await log_game(game)
    except Exception as e:
        print(e)
        return web.Response(text="500: Error, game was not logged!")
    else:
        return web.Response(text="200: Logged!")

def start_cron():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_sql())
    loop.run_until_complete(msh.start())

if __name__ == "__main__":
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    mp.set_start_method("spawn")
    cronprocess = mp.Process(target=start_cron)
    cronprocess.start()
    app.router.add_routes(routes)
    web.run_app(app, port="8000")
