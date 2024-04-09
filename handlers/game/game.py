from sanic import Request

from helpers.sm5helper import get_sm5_player_stats
from helpers.tooltips import TOOLTIP_INFO
from shared import app
from utils import render_template, is_admin
from db.game import EntityEnds, EntityStarts
from db.sm5 import SM5Game, SM5Stats
from db.laserball import LaserballGame, LaserballStats
from helpers.gamehelper import get_team_rosters, get_matchmaking_teams
from db.types import Team
from sanic import exceptions
from helpers.statshelper import sentry_trace, get_sm5_team_score_graph_data, \
    millis_to_time
from numpy import arange
from typing import Optional


async def get_entity_end(entity) -> Optional[EntityEnds]:
    return await EntityEnds.filter(entity=entity).first()

async def get_laserballstats(entity) -> Optional[LaserballStats]:
    return await LaserballStats.filter(entity=entity).first()

@app.get("/game/<type:str>/<id:int>/")
@sentry_trace
async def game_index(request: Request, type: str, id: int) -> str:
    if type == "sm5":
        game: SM5Game = await SM5Game.filter(id=id).prefetch_related("entity_starts", "entity_ends").first()

        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")

        full_stats = await get_sm5_player_stats(game, compute_lives_over_time=True)

        score_chart_data = await get_sm5_team_score_graph_data(game, full_stats.get_teams())

        players_matchmake_team1, players_matchmake_team2 = get_matchmaking_teams(full_stats.get_team_rosters())

        if game.ranked:
            win_chance_after_game = await game.get_win_chance_after_game()
            win_chance_before_game = await game.get_win_chance_before_game()
        else:
            win_chance_after_game = None
            win_chance_before_game = None

        return await render_template(
            request, "game/sm5.html",
            teams=full_stats.teams,
            game=game,
            millis_to_time=millis_to_time,
            score_chart_labels=[t for t in arange(0, 900000 // 1000 // 60 + 0.5, 0.5)],
            score_chart_data=score_chart_data,
            win_chance_before_game=win_chance_before_game,
            win_chance_after_game=win_chance_after_game,
            players_matchmake_team1=players_matchmake_team1,
            players_matchmake_team2=players_matchmake_team2,
            lives_over_time=full_stats.get_lives_over_time_team_average_line_chart(),
            tooltip_info=TOOLTIP_INFO,
            is_admin=is_admin(request)
        )
    elif type == "laserball":
        game = await LaserballGame.filter(id=id).prefetch_related("entity_starts").first()

        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")


        team_rosters = await get_team_rosters(await game.entity_starts.all(), await game.entity_ends.all())

        scores = {
            team: await game.get_team_score(team) for team in team_rosters.keys()
        }

        score_chart_data = await get_sm5_team_score_graph_data(game, list(team_rosters.keys()))

        players_matchmake_team1, players_matchmake_team2 = get_matchmaking_teams(team_rosters)

        # Sort the teams in order of their score.
        team_ranking = sorted(scores.keys(), key=lambda team: scores[team], reverse=True)

        if game.ranked:
            win_chance_after_game = await game.get_win_chance_after_game()
            win_chance_before_game = await game.get_win_chance_before_game()
        else:
            win_chance_after_game = None
            win_chance_before_game = None

        return await render_template(
            request, "game/laserball.html",
            game=game,
            get_entity_end=get_entity_end,
            get_laserballstats=get_laserballstats,
            fire_score=await game.get_team_score(Team.RED),
            ice_score=await game.get_team_score(Team.BLUE),
            score_chart_labels=[{"x": t, "y": await game.get_rounds_at_time(t*60*1000)} for t in arange(0, 900000//1000//60+0.5, 0.5)],
            score_chart_data_red=[await game.get_team_score_at_time(Team.RED, t) for t in range(0, 900000+30000, 30000)],
            score_chart_data_blue=[await game.get_team_score_at_time(Team.BLUE, t) for t in range(0, 900000+30000, 30000)],
            score_chart_data_rounds=[await game.get_rounds_at_time(t) for t in range(0, 900000+30000, 30000)],
            win_chance_before_game=win_chance_before_game,
            win_chance_after_game=win_chance_after_game,
            players_matchmake_team1=players_matchmake_team1,
            players_matchmake_team2=players_matchmake_team2,
            is_admin=is_admin(request)
        )
    else:
        raise exceptions.NotFound("Not found: Invalid game type")