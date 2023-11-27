from sanic import Request
from shared import app
from utils import render_template
from helpers import statshelper, userhelper
from objects import GameType, Team
from helpers.statshelper import sentry_trace
from db.models import SM5Game, Player, EntityEnds, LaserballGame
from tortoise.expressions import F

@app.get("/stats")
@sentry_trace
async def stats(request: Request) -> str:
    total_players = await Player.all().count()
    total_games = await SM5Game.all().count() + await LaserballGame.all().count()
    ranked_games = await SM5Game.filter(ranked=True).count() + await LaserballGame.filter(ranked=True).count()
    total_games_played = await EntityEnds.all().count()
    ranking_accuracy = await statshelper.get_ranking_accuracy()

    sm5_red_wins = await SM5Game.filter(winner=Team.RED, ranked=True).count()
    sm5_green_wins = await SM5Game.filter(winner=Team.GREEN, ranked=True).count()
    points_scored = await statshelper.get_points_scored()
    nukes_launched = await statshelper.get_nukes_launched()
    nukes_cancelled = await statshelper.get_nukes_cancelled()
    medic_hits = await statshelper.get_medic_hits()
    own_medic_hits = await statshelper.get_own_medic_hits()

    top_commanders = await statshelper.get_top_commanders()
    top_heavies = await statshelper.get_top_heavies()
    top_scouts = await statshelper.get_top_scouts()
    top_ammos = await statshelper.get_top_ammos()
    top_medics = await statshelper.get_top_medics()

    laserball_red_wins = await LaserballGame.filter(winner=Team.RED, ranked=True).count()
    laserball_blue_wins = await LaserballGame.filter(winner=Team.BLUE, ranked=True).count()
    goals_scored = await statshelper.get_goals_scored()

    return await render_template(request,
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
    )