from helpers.userhelper import get_median_role_score
from objects import GameType, Team
from utils import render_template, get_post
from shared import app
from sanic import Request, HTTPResponse, response, exceptions
from shared import app
from urllib.parse import unquote
from typing import Union
from db.models import Player, SM5Game, LaserballGame
from helpers.statshelper import sentry_trace

sql = app.ctx.sql

async def get_entity_start(game, player):
    return await game.entity_starts.filter(entity_id=player.ipl_id).first()

async def get_entity_end(game, entity_start):
    return await game.entity_ends.filter(entity=entity_start.id).first()

async def get_sm5_stat(game, entity_start):
    return await game.sm5_stats.filter(entity_id=entity_start.id).first()

async def get_laserball_stat(game, entity_start):
    return await game.laserball_stats.filter(entity=entity_start).first()


async def get_role_labels_from_medians(median_role_score):
    labels = []
    for i, role_score in enumerate(median_role_score):
        if role_score == 0:
            continue
        else:
            if i == 0:
                labels.append("Commander")
            elif i == 1:
                labels.append("Heavy")
            elif i == 2:
                labels.append("Scout")
            elif i == 3: 
                labels.append("Ammo")
            elif i == 4:
                labels.append("Medic")

    return labels
                

@app.get("/player/<id>")
@sentry_trace
async def player_get(request: Request, id: Union[int, str]) -> str:
    id = unquote(id)

    player = await Player.get_or_none(player_id=id)

    if not player:
        try:
            player = await Player.filter(codename=id).first() # could be codename
        except Exception:
            raise exceptions.NotFound("Not found: Invalid ID or codename")
        
    if not player:
        raise exceptions.NotFound("Not found: Invalid ID or codename")
    
    recent_games_sm5 = await SM5Game.filter(entity_starts__entity_id=player.ipl_id).order_by("-start_time").limit(5)
    recent_games_laserball = await LaserballGame.filter(entity_starts__entity_id=player.ipl_id).order_by("-start_time").limit(5)

    favorite_role = await player.get_favorite_role()
    favorite_battlesuit = await player.get_favorite_battlesuit()

    median_role_score = await get_median_role_score(player)
    
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
        role_plot_data_player=[x for x in median_role_score if x != 0],
        role_plot_data_world=await Player.get_median_role_score_world(median_role_score),
        role_plot_labels=await get_role_labels_from_medians(median_role_score),
    )

@app.post("/player")
async def player_post(request: Request) -> str:
    data = get_post(request)
    user = data["userid"]
    return response.redirect(f"/player/{user}")