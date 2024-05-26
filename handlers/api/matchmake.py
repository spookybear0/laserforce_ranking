from sanic import Request
from sanic import response
from sanic.log import logger

from db.player import Player
from db.types import GameType
from helpers import ratinghelper
from helpers.statshelper import sentry_trace
from shared import app


# this api is only used for internal purposes (matchmake page)

@app.get("/api/internal/matchmake/<type_:str>")
@sentry_trace
async def api_matchmake(request: Request, type_: str) -> str:
    # 2-4 teams (team1, team2, ...)

    logger.info(f"Matchmaking requested for {type_}")

    mode = GameType("laserball" if type_ == "laserball" else "sm5")
    matchmake_roles = request.args.get("matchmake_roles") == "true"

    # get the teams

    team1 = request.args.get("team1").strip('][').replace('"', "").split(', ')
    team2 = request.args.get("team2").strip('][').replace('"', "").split(', ')
    team3 = request.args.get("team3").strip('][').replace('"', "").split(', ')
    team4 = request.args.get("team4").strip('][').replace('"', "").split(', ')
    num_teams = int(request.args.get("num_teams", 2))

    if num_teams == 2:
        team3 = []
        team4 = []
    elif num_teams == 3:
        team4 = []

    # get ratings from codenames

    team1_players = []
    team2_players = []
    team3_players = []
    team4_players = []

    def add_unrated_player(team) -> bool:
        if codename == "Unrated Player":
            # dummy class to represent unrated player
            class _: pass

            p = _()
            p.codename = "Unrated Player"
            p.sm5_rating = ratinghelper.Rating(25, 8.333)
            p.laserball_rating = ratinghelper.Rating(25, 8.333)
            team.append(p)
            return True
        return False

    for codename in team1:
        if not add_unrated_player(team1_players):
            team1_players.append(await Player.filter(codename=codename).first())
    for codename in team2:
        if not add_unrated_player(team2_players):
            team2_players.append(await Player.filter(codename=codename).first())
    for codename in team3:
        if not add_unrated_player(team3_players):
            team3_players.append(await Player.filter(codename=codename).first())
    for codename in team4:
        if not add_unrated_player(team4_players):
            team4_players.append(await Player.filter(codename=codename).first())

    # calculate win chances

    all_players = team1_players + team2_players + team3_players + team4_players

    # remove None objects

    all_players = [player for player in all_players if player is not None]

    matchmade_roles = None

    if matchmake_roles:
        matchmade_teams, matchmade_roles = ratinghelper.matchmake_teams_with_roles(all_players, num_teams, mode)
    else:
        matchmade_teams = ratinghelper.matchmake_teams(all_players, num_teams, mode)

    if not team3:
        matchmade_teams.append([])
    if not team4:
        matchmade_teams.append([])

    for i, team in enumerate(matchmade_teams):
        matchmade_teams[i] = {player.codename: (player.sm5_ordinal, player.laserball_ordinal) for player in team}

    return response.json({"teams": matchmade_teams, "roles": matchmade_roles})
