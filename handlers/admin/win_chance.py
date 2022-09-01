from sanic import Request
from helpers import ratinghelper
from utils import render_template
from shared import app
from objects import GameType, Player

@app.get("/admin/win_chance")
async def admin_win_chance_get(request: Request):
    return await render_template(request, "admin/win_calculator.html")

@app.post("/admin/win_chance")
async def admin_win_chance_post(request: Request):
    data = await request.post()

    team1 = []
    team2 = []

    mode = data.get("mode", "sm5")
    if mode == "": mode = "sm5"
    mode = GameType(mode)

    for i in range(8):
        codename = data[f"1player{i}"]
        if codename == "":
            continue
        p = await Player.from_name(codename)
        team1.append(p)

    for i in range(8):
        codename = data[f"2player{i}"]
        if codename == "":
            continue
        p = await Player.from_name(codename)
        team2.append(p)

    win_chance = ratinghelper.get_win_chance(team1, team2)
    draw_chance = round(ratinghelper.get_draw_chance(team1, team2), 3)
    
    # format match

    team1 = ratinghelper.attrgetter(team1, lambda obj: getattr(obj, "codename"))
    team2 = ratinghelper.attrgetter(team2, lambda obj: getattr(obj, "codename"))

    win_chance[0] = round(win_chance[0], 3)
    win_chance[1] = round(win_chance[1], 3)

    return await render_template(request, "admin/win_calculator_results.html", team1=team1, team2=team2, win_chance=win_chance, draw_chance=draw_chance)