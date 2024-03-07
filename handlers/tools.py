from sanic import Request
from shared import app
from helpers import ratinghelper
from utils import render_template, get_post
from objects import GameType
from db.models import Player
from sanic.log import logger
from helpers.statshelper import sentry_trace
from openskill.models import PlackettLuceRating as Rating

class FakePlayer:
    def __init__(self, codename: str) -> None:
        self.codename = codename
        self.sm5_rating = Rating(ratinghelper.ASSUMED_SKILL_MU, ratinghelper.ASSUMED_SKILL_SIGMA)
        self.laserball_rating = Rating(ratinghelper.ASSUMED_SKILL_MU, ratinghelper.ASSUMED_SKILL_SIGMA)
        self.sm5_rating_mu = ratinghelper.ASSUMED_SKILL_MU
        self.sm5_rating_sigma = ratinghelper.ASSUMED_SKILL_SIGMA
        self.laserball_rating_mu = ratinghelper.ASSUMED_SKILL_MU
        self.laserball_rating_sigma = ratinghelper.ASSUMED_SKILL_SIGMA

    def __str__(self) -> str:
        return f"{self.codename} (non member)"
    
    def __repr__(self) -> str:
        return f"{self.codename} (non member)"

@app.get("/tools")
async def tools(request: Request) -> str:
    players = await Player.filter()

    # all_players = {codename: (sm5_rating, lb_rating)
    all_players = {player.codename: (player.sm5_rating.ordinal(), player.laserball_rating.ordinal()) for player in players}

    return await render_template(
        request,
        "tools.html",
        players=players,
        all_players=all_players,
        mode="sm5",
        team1=[],
        team2=[],
    )

@app.post("/tools")
async def tools_post(request: Request) -> str:
    data = request.form

    team1 = []
    team2 = []

    mode = data.get("mode", "sm5")
    if mode == "": mode = "sm5"
    mode = GameType(mode)

    for i in range(16):
        codename = data.get(f"1player{i}")
        if not codename:
            continue
        codename = codename.strip()
        print(codename)
        p = await Player.filter(codename=codename).first()
        print(p)
        print(p.sm5_rating)
        team1.append(p.codename)

    for i in range(16):
        codename = data.get(f"2player{i}")
        if not codename:
            continue
        codename = codename.strip()
        p = await Player.filter(codename=codename).first()
        team2.append(p.codename)

    print(team1, team2)

    players = await Player.filter()

    # all_players = {codename: (sm5_rating, lb_rating)
    all_players = {player.codename: (player.sm5_rating.ordinal(), player.laserball_rating.ordinal()) for player in players}

    return await render_template(
        request,
        "tools.html",
        players=players,
        all_players=all_players,
        mode=mode,
        team1=team1,
        team2=team2,
    )