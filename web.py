from objects import Role, Game, GamePlayer, Team
from glob import get_player_cron_log, get_rank_cron_log
from helpers import fetch_player, get_player, get_total_games, get_total_games_played, legacy_ranking_cron, log_game, init_sql, player_cron, get_top_100, get_top_100_by_role, fetch_player_by_name, get_total_players # type: ignore
from aiohttp import web
from async_cron.job import CronJob # type: ignore
from async_cron.schedule import Scheduler # type: ignore
import multiprocessing as mp
import asyncio
import aiohttp_jinja2
import jinja2
import bcrypt
import os
import traceback

app = web.Application()
routes = web.RouteTableDef()

os.chdir(os.path.dirname(os.path.realpath(__file__)))
templates = aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader("html"))
app.router.add_static("/css/", path="./css/", name="css")

msh = Scheduler()
ranking = CronJob(name="ranking").every(3).hour.go(legacy_ranking_cron)
player = CronJob(name="player").every(6).hour.go(player_cron)
msh.add_job(ranking)
msh.add_job(player)

async def render_template(r, template, *args, **kwargs) -> web.Response:
    text = templates.get_template(template).render(*args, **kwargs)
    return web.Response(text=text, content_type="text/html")

@routes.get("/top")
async def top_get(r: web.RequestHandler):
    await init_sql()
    scout = await get_top_100_by_role(Role.SCOUT)
    heavy = await get_top_100_by_role(Role.HEAVY)
    ammo = await get_top_100_by_role(Role.AMMO)
    medic = await get_top_100_by_role(Role.MEDIC)
    commander = await get_top_100_by_role(Role.COMMANDER)
    return await render_template(r, "top.html", scout=scout, heavy=heavy, ammo=ammo, medic=medic, commander=commander)

@routes.get("/log")
async def log_game_get(r: web.RequestHandler):
    return await render_template(r, "log.html")

@routes.get("/admin/matchmake")
async def matchmake_get(r: web.RequestHandler):
    return await render_template(r, "matchmake.html")

@routes.post("/log")
async def log_game_post(r: web.RequestHandler):
    await init_sql()
    data = await r.post()
    
    # super secure am i right boys
    
    if not bcrypt.checkpw(bytes(data["password"], encoding="utf-8"), b'$2b$10$d85KPH1vMLV20zt0E.0uxOO/Kb3zhgxLp7joElh/K.nnmI/jkTEG.'):
        return web.Response(text="403: Access Denied! (you have been reported to the fbi)")
    
    winner = data["winner"] # green or red
    red_players = []
    green_players = []
    red_game_players = []
    green_game_players = []
    
    for red_player in range(1, 8):
        try:
            player_name = data[f"rname{red_player}"]
            player_role = data[f"rrole{red_player}"]
            player_score = data[f"rscore{red_player}"]
            if player_name == "" or player_role == "" or player_score == "": break
        except KeyError:
            break
        player = await fetch_player_by_name(player_name)
        player_id = player.player_id
        game = GamePlayer(player_id, 0, Team.RED, Role(player_role), int(player_score))
        red_game_players.append(game)
        player.game_player = game
        red_players.append(player)
    for green_player in range(1, 8):
        try:
            player_name = data[f"gname{green_player}"]
            player_role = data[f"grole{green_player}"]
            player_score = data[f"gscore{green_player}"]
            if player_name == "" or player_role == "" or player_score == "": break
        except KeyError:
            break
        player = await fetch_player_by_name(player_name)
        player_id = player.player_id
        game = GamePlayer(player_id, 0, Team.GREEN, Role(player_role), int(player_score))
        green_game_players.append(game)
        player.game_player = game
        green_players.append(player)
        
    players = [*red_players, *green_players]
    
    for player in players:
        if not player.game_player.role.value in ["scout", "heavy", "commander", "medic", "ammo"]:
            return web.Response(text="401: Error, invalid data! (role)")
        if len(player.player_id.split("-")) != 3:
            return web.Response(text="401: Error, invalid data! (id)")
            
    if not winner in ["green", "red"]:
        return web.Response(text="401: Error, invalid data! (team)")
    
    game = Game(0, winner) # game_id is 0 becaue its undefined
    game.players = players
    game.green = green_players
    game.red = red_players
    
    try:
        await log_game(game)
    except Exception as e:
        traceback.print_exc()
        return web.Response(text="500: Error, game was not logged!")
    else:
        return web.Response(text="200: Logged!")
    
@routes.get("/admin")
async def admin_get(r: web.RequestHandler):
    await init_sql()
    total_players = await get_total_players()
    total_games = await get_total_games()
    total_games_played = await get_total_games_played()
    return await render_template(r, "admin.html", total_players=total_players, total_games=total_games, total_games_played=total_games_played)

@routes.get("/admin/players")
async def players_get(r: web.RequestHandler):
    await init_sql()
    page = int(r.rel_url.query.get("page", 0))
    return await render_template(r, "players.html", players=await get_top_100(15, 15*page), page=page)

@routes.get("/admin/player/{id}")
async def player_get(r: web.RequestHandler):
    await init_sql()
    id = r.match_info["id"]
    try:
        player = await get_player(id)
    except IndexError:
        try:
            player = await fetch_player_by_name(id) # could be codename
        except IndexError:
            raise web.HTTPNotFound(reason="Invalid ID")
    return await render_template(r, "player.html", player=player)

@routes.post("/admin/player")
async def player_post(r: web.RequestHandler):
    data = await r.post()
    user = data["userid"]
    raise web.HTTPFound(f"/admin/player/{user}")

@routes.get("/admin/cron")
async def admin_get(r: web.RequestHandler):
    await init_sql()
    return await render_template(r, "cron.html")

@routes.get("/admin/cron/player_stream")
async def admin_cron_player_stream_get(r: web.RequestHandler):
    return web.Response(text=get_player_cron_log(), content_type="text/plain")

@routes.get("/admin/cron/rank_stream")
async def admin_cron_rank_stream_get(r: web.RequestHandler):
    return web.Response(text=get_rank_cron_log(), content_type="text/plain")

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