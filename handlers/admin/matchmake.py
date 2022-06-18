from aiohttp import web
from helpers import ratinghelper
from utils import render_template
from shared import routes
from objects import GameType, Player

@routes.get("/admin/matchmake")
async def admin_matchmake_get(request: web.Request):
    return await render_template(request, "admin/matchmake.html")

@routes.post("/admin/matchmake")
async def admin_matchmake_post(request: web.Request):
    data = await request.post()

    players = []

    mode = data.get("mode", "sm5")
    if mode == "": mode = "sm5"
    mode = GameType(mode)

    for i in range(16):
        codename = data[f"player{i}"]
        if codename == "":
            continue
        p = await Player.from_name(codename)
        players.append(p)

    match = ratinghelper.matchmake_elo(players, mode)

    win_chance = ratinghelper.get_win_chance(*match)
    
    # format match
    
    def key(obj):
        game = []
        for i in range(len(obj)):
            game.append(getattr(obj[i], "codename"))
        return game
    
    match = ratinghelper.attrgetter(list(match), key)

    win_chance[0] = round(win_chance[0], 2)
    win_chance[1] = round(win_chance[1], 2)

    return await render_template(request, "admin/matchmake_results.html", team1=match[0], team2=match[1], win_chance=win_chance)