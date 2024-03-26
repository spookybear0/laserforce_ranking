from sanic import Request


from helpers.gamehelper import get_team_rosters, get_player_display_names, get_matchmaking_teams
from shared import app
from utils import render_template, is_admin
from db.game import EntityEnds, EntityStarts
from db.sm5 import SM5Game, SM5Stats
from db.laserball import LaserballGame, LaserballStats
from db.types import Team
from sanic import exceptions
from helpers.statshelper import sentry_trace
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
        game: SM5Game = await SM5Game.filter(id=id).prefetch_related("entity_starts", "entity_ends").first()

        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")

        team_rosters = await get_team_rosters(game.entity_starts, game.entity_ends)

        players_matchmake_team1, players_matchmake_team2 = get_matchmaking_teams(team_rosters)

        return await render_template(
            request, "game/sm5.html",
            game=game, get_entity_end=get_entity_end,
            get_sm5stats=get_sm5stats,
            fire_score=await game.get_team_score(Team.RED),
            earth_score=await game.get_team_score(Team.GREEN),
            score_chart_labels=[t for t in arange(0, 900000//1000//60+0.5, 0.5)],
            score_chart_data_red=[await game.get_team_score_at_time(Team.RED, t) for t in range(0, 900000+30000, 30000)],
            score_chart_data_green=[await game.get_team_score_at_time(Team.GREEN, t) for t in range(0, 900000+30000, 30000)],
            win_chance=await game.get_win_chance(),
            win_chance_before_game=await game.get_win_chance_before_game(),
            players_matchmake_team1=players_matchmake_team1,
            players_matchmake_team2=players_matchmake_team2,
            is_admin=is_admin(request)
        )
    elif type == "laserball":
        game = await LaserballGame.filter(id=id).prefetch_related("entity_starts", "entity_ends").first()

        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")

        team_rosters = await get_team_rosters(game.entity_starts, game.entity_ends)

        players_matchmake_team1, players_matchmake_team2 = get_matchmaking_teams(team_rosters)

        return await render_template(
            request, "game/laserball.html",
            game=game, get_entity_end=get_entity_end, get_laserballstats=get_laserballstats,
            fire_score=await game.get_team_score(Team.RED),
            ice_score=await game.get_team_score(Team.BLUE),
            score_chart_labels=[{"x": t, "y": await game.get_rounds_at_time(t*60*1000)} for t in arange(0, 900000//1000//60+0.5, 0.5)],
            score_chart_data_red=[await game.get_team_score_at_time(Team.RED, t) for t in range(0, 900000+30000, 30000)],
            score_chart_data_blue=[await game.get_team_score_at_time(Team.BLUE, t) for t in range(0, 900000+30000, 30000)],
            score_chart_data_rounds=[await game.get_rounds_at_time(t) for t in range(0, 900000+30000, 30000)],
            win_chance_before_game=await game.get_win_chance_before_game(),
            win_chance_after_game=await game.get_win_chance_after_game(),
            players_matchmake_team1=players_matchmake_team1,
            players_matchmake_team2=players_matchmake_team2,
            is_admin=is_admin(request)
        )
    else:
        raise exceptions.NotFound("Not found: Invalid game type")