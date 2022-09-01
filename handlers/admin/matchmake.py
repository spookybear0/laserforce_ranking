from sanic import Request
from helpers import ratinghelper
from utils import render_template
from shared import app
from objects import GameType, Player

@app.get("/admin/matchmake")
async def admin_matchmake_get(request: Request):
    return await render_template(request, "admin/matchmake.html")

@app.post("/admin/matchmake")
async def admin_matchmake_post(request: Request):
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

    team1 = match[0]
    team2 = match[1]

    win_chance = ratinghelper.get_win_chance(*match)
    draw_chance = round(ratinghelper.get_draw_chance(team1, team2), 3)
    
    # format match
    
    def key(obj):
        game = []
        for i in range(len(obj)):
            game.append(getattr(obj[i], "codename"))
        return game
    
    match = ratinghelper.attrgetter(list(match), key)

    win_chance[0] = round(win_chance[0], 2)
    win_chance[1] = round(win_chance[1], 2)

    return await render_template(request, "admin/matchmake_results.html", team1=match[0], team2=match[1], win_chance=win_chance, draw_chance=draw_chance)