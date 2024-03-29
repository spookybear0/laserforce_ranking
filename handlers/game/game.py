from itertools import chain

from sanic import Request

from helpers.gamehelper import SM5_STATE_LABEL_MAP, SM5_STATE_COLORS
from shared import app
from utils import render_template, is_admin
from db.game import EntityEnds, EntityStarts
from db.sm5 import SM5Game, SM5Stats
from db.laserball import LaserballGame, LaserballStats
from helpers.gamehelper import get_team_rosters, get_matchmaking_teams
from db.types import Team
from sanic import exceptions
from helpers.statshelper import sentry_trace, get_sm5_team_score_graph_data, get_sm5_player_alive_times, \
    get_player_state_distribution, get_player_state_distribution_pie_chart
from numpy import arange
from typing import List, Optional


async def get_entity_end(entity) -> Optional[EntityEnds]:
    return await EntityEnds.filter(entity=entity).first()

async def get_sm5stats(entity) -> Optional[SM5Stats]:
    return await SM5Stats.filter(entity=entity).first()

async def get_laserballstats(entity) -> Optional[LaserballStats]:
    return await LaserballStats.filter(entity=entity).first()

@app.get("/game/<type:str>/<id:int>/")
@sentry_trace
async def game_index(request: Request, type: str, id: int) -> str:
    if type == "sm5":
        game: SM5Game = await SM5Game.filter(id=id).prefetch_related("entity_starts").first()

        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")

        game_duration = await game.get_actual_game_duration()
        team_rosters = await get_team_rosters(await game.entity_starts.all(), await game.entity_ends.all())

        # Get a flat list of all players across all teams.
        all_players = list(chain.from_iterable(team_rosters.values()))

        scores = {
            team: await game.get_team_score(team) for team in team_rosters.keys()
        }

        time_in_game_values = {
            player.entity_end.id: get_sm5_player_alive_times(game_duration, player.entity_end) for player in
            all_players if player
        }

        uptime_values = {
            player.entity_end.id: get_player_state_distribution_pie_chart(
                await get_player_state_distribution(player.entity_start, player.entity_end,
                                                    game.player_states, game.events, SM5_STATE_LABEL_MAP),
                SM5_STATE_COLORS)
            for player in
            all_players if player
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
            request, "game/sm5.html",
            team_ranking=team_ranking,
            team_rosters=team_rosters,
            scores=scores,
            game=game,
            time_in_game_values=time_in_game_values,
            uptime_values=uptime_values,
            get_sm5stats=get_sm5stats,
            score_chart_labels=[t for t in arange(0, 900000 // 1000 // 60 + 0.5, 0.5)],
            score_chart_data=score_chart_data,
            win_chance_before_game=win_chance_before_game,
            win_chance_after_game=win_chance_after_game,
            players_matchmake_team1=players_matchmake_team1,
            players_matchmake_team2=players_matchmake_team2,
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