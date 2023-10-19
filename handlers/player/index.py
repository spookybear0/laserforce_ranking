from helpers.userhelper import get_median_role_score
from objects import GameType, Team
from utils import render_template, get_post
from helpers import gamehelper
from shared import app
from sanic import Request, HTTPResponse, response, exceptions
from shared import app
from urllib.parse import unquote
from typing import Union
from db.models import Player, SM5Game, LaserballGame
from helpers.statshelper import sentry_trace
from statistics import NormalDist
from numpy import arange

sql = app.ctx.sql

async def get_entity_start(game, player):
    return await game.entity_starts.filter(entity_id=player.ipl_id).first()

async def get_entity_end(game, entity_start):
    return await game.entity_ends.filter(entity=entity_start.id).first()

async def get_sm5_stat(game, entity_start):
    return await game.sm5_stats.filter(entity_id=entity_start.id).first()

async def get_laserball_stat(game, entity_start):
    return await game.laserball_stats.filter(entity=entity_start).first()

@app.get("/player/<id>")
@sentry_trace
async def player_get(request: Request, id: Union[int, str]):
    id = unquote(id)

    player = await Player.get_or_none(player_id=id)

    if not player:
        try:
            player = await Player.filter(codename=id).first() # could be codename
        except Exception:
            raise exceptions.NotFound("Not found: Invalid ID or codename")
    
    recent_games_sm5 = await SM5Game.filter(entity_starts__entity_id=player.ipl_id).order_by("-start_time").limit(5)
    recent_games_laserball = await LaserballGame.filter(entity_starts__entity_id=player.ipl_id).order_by("-start_time").limit(5)

    favorite_role = await player.get_favorite_role()
    favorite_battlesuit = await player.get_favorite_battlesuit()

    # display representation of gaussian distribution

    dist = [(x, NormalDist(player.sm5_mu, player.sm5_sigma).pdf(x)) for x in arange(0, 100)]

    min_ = None
    max_ = None

    for x, pdf in dist:
        if pdf > 0.00001:
            min_ = x
            break

    for x, pdf in dist[::-1]:
        print(x, pdf)
        if pdf > 0.00001:
            max_ = x
            break

    print(min_, max_)
    
    return await render_template(
        request, "player/player.html",
        # general player info
        player=player,
        recent_games_sm5=recent_games_sm5,
        recent_games_laserball=recent_games_laserball,
        get_entity_start=get_entity_start,
        get_entity_end=get_entity_end,
        get_sm5_stat=get_sm5_stat,
        get_laserball_stat=get_laserball_stat,
        favorite_role=favorite_role,
        favorite_battlesuit=favorite_battlesuit,
        # team rate pies (sm5/laserball)
        red_teams_sm5=await player.times_played_as_team(Team.RED, GameType.SM5),
        green_teams_sm5=await player.times_played_as_team(Team.GREEN, GameType.SM5),
        red_teams_laserball=await player.times_played_as_team(Team.RED, GameType.LASERBALL),
        blue_teams_laserball=await player.times_played_as_team(Team.BLUE, GameType.LASERBALL),
        # win percents (sm5, laserball, all)
        sm5_win_percent=await player.get_win_percent(GameType.SM5),
        laserball_win_percent=await player.get_win_percent(GameType.LASERBALL),
        win_percent=await player.get_win_percent(),
        # games won as team (sm5, laserball)
        red_wins_sm5=await player.get_wins_as_team(Team.RED, GameType.SM5),
        green_wins_sm5=await player.get_wins_as_team(Team.GREEN, GameType.SM5),
        red_wins_laserball=await player.get_wins_as_team(Team.RED, GameType.LASERBALL),
        blue_wins_laserball=await player.get_wins_as_team(Team.BLUE, GameType.LASERBALL),
        # role score plot (sm5)
        role_plot_data_player=await player.get_median_role_score(),
        role_plot_data_world=await Player.get_median_role_score_world(),
        # bull curve (sm5)
        bell_curve_x=list(arange(min_-1, max_+2, 0.5)),
        bell_curve_y=[NormalDist(player.sm5_mu, player.sm5_sigma).pdf(x) for x in arange(min_-1, max_+2, 0.5)]
    )

@app.post("/player")
async def player_post(request: Request):
    data = get_post(request)
    user = data["userid"]
    return response.redirect(f"/player/{user}")