from sanic import Request
from sanic.log import logger

from db.game import EntityEnds
from db.laserball import LaserballGame
from db.player import Player
from db.sm5 import SM5Game
from db.types import Team, IntRole
from helpers import statshelper
from helpers.cachehelper import cache_template, precache_template
from helpers.statshelper import sentry_trace
from shared import app
from utils import render_cached_template


@app.get("/stats")
@sentry_trace
@cache_template(ttl=60*60*24)  # Cache for 24 hours
@precache_template()
async def stats(request: Request) -> str:
    logger.info("Loading stats page")

    logger.debug("Loading general stats")

    total_players = await Player.all().count()
    total_games = await SM5Game.all().count() + await LaserballGame.all().count()
    ranked_games = await SM5Game.filter(ranked=True).count() + await LaserballGame.filter(ranked=True).count()
    total_games_played = await EntityEnds.all().count()
    ranking_accuracy = await statshelper.get_ranking_accuracy()
    
    logger.debug("Loading SM5 stats")

    sm5_red_wins = await SM5Game.filter(winner=Team.RED, ranked=True).count()
    sm5_green_wins = await SM5Game.filter(winner=Team.GREEN, ranked=True).count()
    points_scored = await statshelper.get_points_scored()
    nukes_launched = await statshelper.get_nukes_launched()
    nukes_cancelled = await statshelper.get_nukes_cancelled()
    medic_hits = await statshelper.get_medic_hits()
    own_medic_hits = await statshelper.get_own_medic_hits()

    logger.debug("Loading SM5 role stats")

    top_commanders = await statshelper.get_top_role_players(5, IntRole.COMMANDER, 5)
    top_heavies = await statshelper.get_top_role_players(5, IntRole.HEAVY, 5)
    top_scouts = await statshelper.get_top_role_players(5, IntRole.SCOUT, 5)
    top_ammos = await statshelper.get_top_role_players(5, IntRole.AMMO, 5)
    top_medics = await statshelper.get_top_role_players(5, IntRole.MEDIC, 5)

    logger.debug("Loading laserball stats")

    laserball_red_wins = await LaserballGame.filter(winner=Team.RED, ranked=True).count()
    laserball_blue_wins = await LaserballGame.filter(winner=Team.BLUE, ranked=True).count()
    goals_scored = await statshelper.get_goals_scored()
    assists = await statshelper.get_assists()
    passes = await statshelper.get_passes()
    steals = await statshelper.get_steals()
    clears = await statshelper.get_clears()
    blocks = await statshelper.get_blocks()

    logger.debug("Rendering stats page")

    return await render_cached_template(request,
                                        "stats.html",
                                        zip=zip,

                                        # general stats

                                        total_players=total_players,
                                        total_games=total_games,
                                        ranked_games=ranked_games,
                                        total_games_played=total_games_played,
                                        ranking_accuracy=ranking_accuracy,

                                        # sm5 stats

                                        sm5_red_wins=sm5_red_wins,
                                        sm5_green_wins=sm5_green_wins,
                                        points_scored=points_scored,
                                        nukes_launched=nukes_launched,
                                        nukes_cancelled=nukes_cancelled,
                                        medic_hits=medic_hits,
                                        own_medic_hits=own_medic_hits,

                                        # sm5 role stats

                                        top_commanders=top_commanders,
                                        top_heavies=top_heavies,
                                        top_scouts=top_scouts,
                                        top_ammos=top_ammos,
                                        top_medics=top_medics,

                                        # laserball stats

                                        laserball_red_wins=laserball_red_wins,
                                        laserball_blue_wins=laserball_blue_wins,
                                        goals_scored=goals_scored,
                                        assists=assists,
                                        passes=passes,
                                        steals=steals,
                                        clears=clears,
                                        blocks=blocks
                                        )
