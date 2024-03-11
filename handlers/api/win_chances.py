

from sanic import Request
from shared import app
from db.models import Player, GameType
from sanic import response
from sanic.log import logger
from helpers import ratinghelper
from helpers.statshelper import sentry_trace

@app.get("/api/<type_:str>/win_chances")
@sentry_trace
async def api_win_chances(request: Request, type_: str) -> str:
    # 2-4 teams (team1, team2, ...)

    logger.info(f"Win chances requested for {type_}")

    mode = GameType("laserball" if type_ == "laserball" else "sm5")

    # get the teams

    team1 = request.args.get("team1").strip('][').replace('"', "").split(', ')
    team2 = request.args.get("team2").strip('][').replace('"', "").split(', ')
    team3 = request.args.get("team3").strip('][').replace('"', "").split(', ')
    team4 = request.args.get("team4").strip('][').replace('"', "").split(', ')

    if not team1 or team1[0] == "":
        team1 = []
    if not team2 or team2[0] == "":
        team2 = []
    if not team3 or team3[0] == "":
        team3 = []
    if not team4 or team4[0] == "":
        team4 = []

    # get ratings from codenames
        
    team1_players = []
    team2_players = []
    team3_players = []
    team4_players = []

    async def add_unrated_player(team) -> bool:
        if codename == "Unrated Player" or await Player.filter(codename=codename).first() is None:
            # dummy class to represent unrated player
            class _: pass
            p = _()
            p.codename = "Unrated Player"
            p.sm5_rating = ratinghelper.Rating(ratinghelper.MU, ratinghelper.SIGMA)
            p.laserball_rating = ratinghelper.Rating(ratinghelper.MU, ratinghelper.SIGMA)
            team.append(p)
            return True
        return False

    for codename in team1:
        if not await add_unrated_player(team1_players):
            team1_players.append(await Player.filter(codename=codename).first())
    for codename in team2:
        if not await add_unrated_player(team2_players):
            team2_players.append(await Player.filter(codename=codename).first())
    for codename in team3:
        if not await add_unrated_player(team3_players):
            team3_players.append(await Player.filter(codename=codename).first())
    for codename in team4:
        if not await add_unrated_player(team4_players):
            team4_players.append(await Player.filter(codename=codename).first())

    # calculate win chances
        
    win_chances = ratinghelper.get_win_chances(team1_players, team2_players, team3_players, team4_players, mode)

    if not team3:
        win_chances.append(0)
    if not team4:
        win_chances.append(0)

    return response.json(win_chances)