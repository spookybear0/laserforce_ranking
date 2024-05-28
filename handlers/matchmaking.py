from openskill.models import PlackettLuceRating as Rating
from sanic import Request, exceptions
from sanic.log import logger

from db.player import Player
from helpers import ratinghelper
from shared import app
from utils import render_template


class FakePlayer:
    def __init__(self, codename: str) -> None:
        self.codename = codename
        self.sm5_rating = Rating(ratinghelper.MU, ratinghelper.SIGMA)
        self.laserball_rating = Rating(ratinghelper.MU, ratinghelper.SIGMA)
        self.sm5_rating_mu = ratinghelper.MU
        self.sm5_rating_sigma = ratinghelper.SIGMA
        self.laserball_rating_mu = ratinghelper.MU
        self.laserball_rating_sigma = ratinghelper.SIGMA

    @property
    def sm5_ordinal(self) -> int:
        return self.sm5_rating.ordinal()
    
    @property
    def laserball_ordinal(self) -> int:
        return self.laserball_rating.ordinal()

    def __str__(self) -> str:
        return f"{self.codename} (non member)"

    def __repr__(self) -> str:
        return f"{self.codename} (non member)"


@app.get("/matchmaking")
async def matchmaking(request: Request) -> str:
    players = await Player.all()

    # all_players = {codename: (sm5_rating, lb_rating)
    logger.debug("Getting ratings for all players")
    all_players = {player.codename: (player.sm5_rating.ordinal(), player.laserball_rating.ordinal()) for player in
                   players}

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

    logger.debug(f"Matchmaking with mode: {mode}")

    players = await Player.all()

    # all_players = {codename: (sm5_rating, lb_rating)
    logger.debug("Getting ratings for all players")
    all_players = {player.codename: (player.sm5_rating.ordinal(), player.laserball_rating.ordinal()) for player in
                   players}

    logger.debug("Getting players from team 1")

    for i in range(16):
        codename = data.get(f"1player{i}")
        if not codename:
            continue
        codename = codename.strip()

        player = await Player.filter(codename=codename).first()
        if player: # member
            all_players.pop(player.codename, None)
            players.remove(player)
        else:  # non member
            player = FakePlayer(codename)

        if not player:
            return exceptions.BadRequest(f"Player {codename} not found")

        team1.append((player.codename, player.sm5_ordinal, player.laserball_ordinal))

    logger.debug("Getting players from team 2")

    for i in range(16):
        codename = data.get(f"2player{i}")
        if not codename:
            continue
        codename = codename.strip()

        player = await Player.filter(codename=codename).first()
        if player:
            all_players.pop(player.codename, None)
            players.remove(player)
        else:  # non member
            player = FakePlayer(codename)

        if not player:
            return exceptions.BadRequest(f"Player {codename} not found")

        team2.append((player.codename, player.sm5_ordinal, player.laserball_ordinal))

    return await render_template(
        request,
        "matchmaking.html",
        players=players,
        all_players=all_players,
        mode=mode,
        team1=team1,
        team2=team2
    )
