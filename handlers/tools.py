from sanic import Request
from shared import app
from helpers import ratinghelper
from utils import render_template, get_post
from objects import GameType
from db.models import Player
from sanic.log import logger
from helpers.statshelper import sentry_trace
from openskill.models import PlackettLuceRating as Rating

@app.get("/tools")
async def tools(request: Request):
    return await render_template(request, "tools.html")

@app.post("/matchmake")
@sentry_trace
async def matchmake_post(request: Request):
    logger.debug("Matchmaking")

    data = request.form

    players = []

    mode = data.get("mode", "sm5")
    if mode == "": mode = "sm5"
    mode = GameType(mode)

    for i in range(16):
        try:
            codename = data[f"player{i}"][0]
        except KeyError:
            continue
        if codename == "":
            continue
        p = await Player.filter(codename=codename).first()
        if p is None:
            p = lambda: None # dummy object
            p.codename = codename
            p.sm5_rating_mu = 25
            p.sm5_rating_sigma = 25 / 3
            p.sm5_rating = Rating(p.sm5_rating_mu, p.sm5_rating_sigma)
            p.laserball_rating_mu = 25
            p.laserball_rating_sigma = 25 / 3
            p.laserball_rating = Rating(p.laserball_rating_mu, p.laserball_rating_sigma)
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
    data = request.form

    team1 = []
    team2 = []

    mode = data.get("mode")
    if not mode: mode = "sm5"
    mode = GameType(mode)

    for i in range(8):
        codename = data.get(f"1player{i}")
        if not codename:
            continue
        p = await Player.filter(codename=codename).first()
        team1.append(p)

    for i in range(8):
        codename = data.get(f"2player{i}")
        if not codename:
            continue
        p = await Player.filter(codename=codename).first()
        team2.append(p)

    win_chance = ratinghelper.get_win_chance(team1, team2)
    draw_chance = round(ratinghelper.get_draw_chance(team1, team2), 3)
    
    # format match

    for i in range(len(team1)):
        team1[i] = team1[i].codename

    for i in range(len(team2)):
        team2[i] = team2[i].codename

    win_chance[0] = round(win_chance[0], 3)
    win_chance[1] = round(win_chance[1], 3)

    return await render_template(request, "win_calculator_results.html", team1=team1, team2=team2, win_chance=win_chance, draw_chance=draw_chance)