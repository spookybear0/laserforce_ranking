from sanic import Request, exceptions
from shared import app
from helpers import ratinghelper
from utils import render_template, get_post
from objects import GameType
from db.models import Player
from sanic.log import logger
from helpers.statshelper import sentry_trace
from openskill.models import PlackettLuceRating as Rating

@app.get("/matchmaking")
async def matchmaking(request: Request) -> str:
    players = await Player.all()

    # all_players = {codename: (sm5_rating, lb_rating)
    logger.debug("Getting ratings for all players")
    all_players = {player.codename: (player.sm5_rating.ordinal(), player.laserball_rating.ordinal()) for player in players}

    return await render_template(
        request,
        "matchmaking.html",
        players=players,
        all_players=all_players,
        mode="sm5",
        team1=[],
        team2=[],
    )

@app.post("/matchmaking")
async def matchmaking_post(request: Request) -> str:
    data = request.form

    team1 = []
    team2 = []

    mode = data.get("mode", "sm5")
    if mode == "": mode = "sm5"
    mode = GameType(mode)

    logger.debug(f"Matchmaking with mode: {mode}")

    logger.debug("Getting players from team 1")

    for i in range(16):
        codename = data.get(f"1player{i}")
        if not codename:
            continue
        codename = codename.strip()
        player = await Player.filter(codename=codename).first()

        if not player:
            return exceptions.BadRequest(f"Player {codename} not found")

        team1.append(player.codename)

    logger.debug("Getting players from team 2")

    for i in range(16):
        codename = data.get(f"2player{i}")
        if not codename:
            continue
        codename = codename.strip()
        player = await Player.filter(codename=codename).first()

        if not player:
            return exceptions.BadRequest(f"Player {codename} not found")

        team2.append(player.codename)

    players = await Player.all()

    # all_players = {codename: (sm5_rating, lb_rating)
    logger.debug("Getting ratings for all players")
    all_players = {player.codename: (player.sm5_rating.ordinal(), player.laserball_rating.ordinal()) for player in players}

    return await render_template(
        request,
        "matchmaking.html",
        players=players,
        all_players=all_players,
        mode=mode,
        team1=team1,
        team2=team2
    )