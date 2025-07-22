from typing import Optional

from numpy import arange
from sanic import Request
from sanic import exceptions
from sanic.log import logger

from db.game import EntityEnds
from db.laserball import LaserballGame, LaserballStats, Team as LaserballTeam
from db.sm5 import SM5Game, Team as SM5Team
from helpers.cachehelper import cache_template
from helpers.gamehelper import get_matchmaking_teams
from helpers.laserballhelper import get_laserball_player_stats
from helpers.sm5helper import get_sm5_player_stats, get_sm5_notable_events
from helpers.statshelper import sentry_trace, get_sm5_team_score_graph_data, \
    millis_to_time
from shared import app
from utils import is_admin, render_cached_template


async def get_entity_end(entity) -> Optional[EntityEnds]:
    return await EntityEnds.filter(entity=entity).first()


async def get_laserballstats(entity) -> Optional[LaserballStats]:
    return await LaserballStats.filter(entity=entity).first()


@app.get("/game/<type:str>/<id:int>/")
@sentry_trace
@cache_template()
async def game_index(request: Request, type: str, id: int) -> str:
    if type == "sm5":
        logger.debug(f"Fetching sm5 game with ID {id}")

        game: SM5Game = await SM5Game.filter(id=id).prefetch_related("entity_starts", "entity_ends").first()

        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")

        logger.debug(f"Game found: {game}")

        logger.debug("Fetching player stats")

        full_stats = await get_sm5_player_stats(game, compute_lives_over_time=True)

        logger.debug("Fetching team score graph data")

        score_chart_data = await get_sm5_team_score_graph_data(game, full_stats.get_teams())

        logger.debug("Fetching matchmaking teams")

        players_matchmake_team1, players_matchmake_team2 = get_matchmaking_teams(full_stats.get_team_rosters())

        logger.debug("Fetching win chances")

        if game.ranked:
            win_chance_after_game = await game.get_win_chance_after_game()
            win_chance_before_game = await game.get_win_chance_before_game()
        else:
            win_chance_after_game = None
            win_chance_before_game = None

        logger.debug("Fetching notable events")

        notable_events = await get_sm5_notable_events(game)

        logger.debug("Rendering template")

        return await render_cached_template(
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
            notable_events=notable_events,
            # TODO: remove this in favor of "team1" and "team2" scores
            fire_score=await game.get_team_score(SM5Team.RED),
            earth_score=await game.get_team_score(SM5Team.GREEN),
            is_admin=is_admin(request)
        )
    elif type == "laserball":
        game = await LaserballGame.filter(id=id).prefetch_related("entity_starts", "entity_ends").first()

        logger.debug(f"Fetching laserball game with ID {id}")

        if not game:
            raise exceptions.NotFound("Not found: Invalid game ID")

        game_duration = game.mission_duration

        logger.debug(f"Game found: {game}")

        logger.debug("Fetching team rosters")

        full_stats = await get_laserball_player_stats(game)

        logger.debug("Fetching matchmaking teams")

        players_matchmake_team1, players_matchmake_team2 = get_matchmaking_teams(full_stats.get_team_rosters())

        logger.debug("Fetching win chances")

        if game.ranked:
            win_chance_after_game = await game.get_win_chance_after_game()
            win_chance_before_game = await game.get_win_chance_before_game()
        else:
            win_chance_after_game = None
            win_chance_before_game = None

        logger.debug("Fetching teams for scores")

        teams = await game.get_teams()

        logger.debug("Rendering template")

        return await render_cached_template(
            request, "game/laserball.html",
            game=game,
            teams=full_stats.teams,
            score_chart_labels=[{"x": t, "y": await game.get_rounds_at_time(t * 60 * 1000)} for t in
                                arange(0, game_duration // 1000 // 60 + 0.5, 0.5)],
            score_chart_data=full_stats.score_chart_data,
            score_chart_data_rounds=full_stats.score_chart_data_rounds,
            win_chance_before_game=win_chance_before_game,
            win_chance_after_game=win_chance_after_game,
            players_matchmake_team1=players_matchmake_team1,
            players_matchmake_team2=players_matchmake_team2,
            team1_score=await game.get_team_score(teams[0].enum),
            team2_score=await game.get_team_score(teams[1].enum),
            is_admin=is_admin(request)
        )
    else:
        raise exceptions.BadRequest("Invalid game type")
