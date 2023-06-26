from sanic import Request
from shared import app
from helpers import ratinghelper
from utils import render_template, get_post
from objects import GameType, Player
from sanic.log import logger
from helpers.statshelper import sentry_trace

@app.get("/tools")
async def tools(request: Request):
    return await render_template(request, "tools.html")

@app.post("/matchmake")
@sentry_trace
async def matchmake_post(request: Request):
    logger.debug("Matchmaking")

    data = get_post(request)
    print(data)

    players = []

    mode = data.get("mode", "sm5")
    if mode == "": mode = "sm5"
    mode = GameType(mode)

    for i in range(16):
        try:
            codename = data[f"player{i}"]
        except KeyError:
            continue
        if codename == "":
            continue
        p = await Player.from_name(codename)
        players.append(p)

    match = ratinghelper.matchmake(players, mode)

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
    
    match = list(map(key, list(match)))

    win_chance[0] = round(win_chance[0], 2)
    win_chance[1] = round(win_chance[1], 2)

    return await render_template(request, "matchmake_results.html", team1=match[0], team2=match[1], win_chance=win_chance, draw_chance=draw_chance)

@app.post("/win_chance")
async def win_chance_post(request: Request):
    data = dict(get_post(request))

    team1 = []
    team2 = []

    mode = data.get("mode")
    if not mode: mode = "sm5"
    mode = GameType(mode)

    for i in range(8):
        codename = data.get(f"1player{i}")
        if not codename:
            continue
        p = await Player.from_name(codename)
        team1.append(p)

    for i in range(8):
        codename = data.get(f"2player{i}")
        if not codename:
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

    return await render_template(request, "win_calculator_results.html", team1=team1, team2=team2, win_chance=win_chance, draw_chance=draw_chance)