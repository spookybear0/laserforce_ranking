from helpers.laserballhelper import get_laserball_rating_over_time
from helpers.sm5helper import get_sm5_rating_over_time
from helpers.userhelper import get_median_role_score
from db.types import GameType, Team
from utils import render_cached_template, get_post
from shared import app
from sanic import Request, HTTPResponse, response, exceptions
from shared import app
from urllib.parse import unquote
from typing import Union, Optional
from db.player import Player
from db.sm5 import SM5Game, SM5Stats
from db.laserball import LaserballGame, LaserballStats
from db.game import EntityEnds, EntityStarts
from helpers.statshelper import sentry_trace, create_time_series_ordered_graph
from sanic.log import logger
from helpers.cachehelper import cache_template

_GAMES_PER_PAGE = 5

sql = app.ctx.sql

async def get_entity_start(game, player) -> Optional[EntityStarts]:
    return await game.entity_starts.filter(entity_id=player.entity_id).first()

async def get_entity_end(game, entity_start) -> Optional[EntityEnds]:
    return await game.entity_ends.filter(entity=entity_start.id).first()

async def get_sm5_stat(game, entity_start) -> Optional[SM5Stats]:
    return await game.sm5_stats.filter(entity_id=entity_start.id).first()

async def get_laserball_stat(game, entity_start) -> Optional[LaserballStats]:
    return await game.laserball_stats.filter(entity=entity_start).first()


async def get_role_labels_from_medians(median_role_score) -> list:
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
@cache_template()
async def player_get(request: Request, id: Union[int, str]) -> str:
    sm5page = int(request.args.get("sm5page", 0))
    lbpage = int(request.args.get("lbpage", 0))

    id = unquote(id)

    player = await Player.get_or_none(player_id=id)

    if not player:
        try:
            player = await Player.filter(codename=id).first() # could be codename
        except Exception:
            raise exceptions.NotFound("Not found: Invalid ID or codename")
        
    if not player:
        raise exceptions.NotFound("Not found: Invalid ID or codename")
    
    logger.info(f"Loading player page for {player}")

    logger.debug("Loading recent games")
    
    recent_games_sm5 = await SM5Game.filter(entity_starts__entity_id=player.entity_id).order_by("-start_time").limit(5).offset(_GAMES_PER_PAGE * sm5page)
    recent_games_laserball = await LaserballGame.filter(entity_starts__entity_id=player.entity_id).order_by("-start_time").limit(5).offset(_GAMES_PER_PAGE * lbpage)

    median_role_score = await get_median_role_score(player)

    logger.debug("Loading team rate pies")

    red_teams_sm5 = await player.times_played_as_team(Team.RED, GameType.SM5)
    green_teams_sm5 = await player.times_played_as_team(Team.GREEN, GameType.SM5)
    red_teams_laserball = await player.times_played_as_team(Team.RED, GameType.LASERBALL)
    blue_teams_laserball = await player.times_played_as_team(Team.BLUE, GameType.LASERBALL)

    logger.debug("Loading win percents")

    red_wins_sm5 = await player.get_wins_as_team(Team.RED, GameType.SM5)
    green_wins_sm5 = await player.get_wins_as_team(Team.GREEN, GameType.SM5)
    red_wins_laserball = await player.get_wins_as_team(Team.RED, GameType.LASERBALL)
    blue_wins_laserball = await player.get_wins_as_team(Team.BLUE, GameType.LASERBALL)

    sm5_win_percent = (red_wins_sm5+green_wins_sm5)/(red_teams_sm5+green_teams_sm5) if (red_teams_sm5+green_teams_sm5) != 0 else 0
    laserball_win_percent = (red_wins_laserball+blue_wins_laserball)/(red_teams_laserball+blue_teams_laserball) if (red_teams_laserball+blue_teams_laserball) != 0 else 0
    win_percent = (red_wins_sm5+green_wins_sm5+red_wins_laserball+blue_wins_laserball)/(red_teams_sm5+green_teams_sm5+red_teams_laserball+blue_teams_laserball) if (red_teams_sm5+green_teams_sm5+red_teams_laserball+blue_teams_laserball) != 0 else 0
    
    logger.debug("Loading stat chart")

    times_played_sm5 = red_teams_sm5+green_teams_sm5
    favorite_role_sm5 = await player.get_favorite_role()
    favorite_battlesuit_sm5 = await player.get_favorite_battlesuit(GameType.SM5)
    sean_hits_sm5 = await player.get_sean_hits(GameType.SM5)
    sm5_shots_hit = await player.get_shots_hit(GameType.SM5)
    sm5_shots_fired = await player.get_shots_fired(GameType.SM5)

    logger.debug("Loading laserball stat chart")

    # no roles in laserball
    times_played_laserball = red_teams_laserball+blue_teams_laserball
    favorite_battlesuit_laserball = await player.get_favorite_battlesuit(GameType.LASERBALL)
    sean_hits_laserball = await player.get_sean_hits(GameType.LASERBALL)
    laserball_shots_hit = await player.get_shots_hit(GameType.LASERBALL)
    laserball_shots_fired = await player.get_shots_fired(GameType.LASERBALL)

    logger.debug("Loading overall stat chart")

    times_played = times_played_sm5+times_played_laserball
    favorite_battlesuit = await player.get_favorite_battlesuit()
    sean_hits = sean_hits_sm5+sean_hits_laserball
    shots_hit = sm5_shots_hit+laserball_shots_hit
    shots_fired = sm5_shots_fired+laserball_shots_fired

    sm5_rating_raw_data = await get_sm5_rating_over_time(player.entity_id)
    sm5_rating_graph_data = create_time_series_ordered_graph(sm5_rating_raw_data, 100)

    sm5_rating_over_time_labels = sm5_rating_graph_data.labels
    sm5_rating_over_time_data = sm5_rating_graph_data.data_points

    laserball_rating_raw_data = await get_laserball_rating_over_time(player.entity_id)
    laserball_rating_graph_data = create_time_series_ordered_graph(laserball_rating_raw_data, 100)

    laserball_rating_over_time_labels = laserball_rating_graph_data.labels
    laserball_rating_over_time_data = laserball_rating_graph_data.data_points

    logger.debug("Rendering player page")

    return await render_cached_template(
        request, "player/player.html",
        # general player info
        player=player,
        recent_games_sm5=recent_games_sm5,
        recent_games_laserball=recent_games_laserball,
        get_entity_start=get_entity_start,
        get_entity_end=get_entity_end,
        get_sm5_stat=get_sm5_stat,
        get_laserball_stat=get_laserball_stat,
        sm5page=sm5page,
        lbpage=lbpage,
        # team rate pies (sm5/laserball)
        red_teams_sm5=red_teams_sm5,
        green_teams_sm5=green_teams_sm5,
        red_teams_laserball=red_teams_laserball,
        blue_teams_laserball=blue_teams_laserball,
        # win percents (sm5, laserball, all)
        sm5_win_percent=sm5_win_percent,
        laserball_win_percent=laserball_win_percent,
        win_percent=win_percent,
        # games won as team (sm5, laserball)
        red_wins_sm5=red_wins_sm5,
        green_wins_sm5=green_wins_sm5,
        red_wins_laserball=red_wins_laserball,
        blue_wins_laserball=blue_wins_laserball,
        # role score plot (sm5)
        role_plot_data_player=[x for x in median_role_score if x != 0],
        role_plot_data_world=await Player.get_median_role_score_world(median_role_score),
        role_plot_labels=await get_role_labels_from_medians(median_role_score),
        # total number of roles that aren't 0
        role_plot_total_roles=len([x for x in median_role_score if x != 0]),
        # stat chart
        # sm5
        times_played_sm5=times_played_sm5,
        favorite_role_sm5=favorite_role_sm5,
        favorite_battlesuit_sm5=favorite_battlesuit_sm5,
        sean_hits_sm5=sean_hits_sm5,
        shots_hit_sm5=sm5_shots_hit,
        shots_fired_sm5=sm5_shots_fired,
        # laserball
        times_played_laserball=times_played_laserball,
        favorite_battlesuit_laserball=favorite_battlesuit_laserball,
        sean_hits_laserball=sean_hits_laserball,
        shots_hit_laserball=laserball_shots_hit,
        shots_fired_laserball=laserball_shots_fired,
        # overall
        times_played=times_played,
        favorite_battlesuit=favorite_battlesuit,
        sean_hits=sean_hits,
        shots_hit=shots_hit,
        shots_fired=shots_fired,
        # rating over time
        sm5_rating_over_time_labels=sm5_rating_over_time_labels,
        sm5_rating_over_time_data=sm5_rating_over_time_data,
        laserball_rating_over_time_labels=laserball_rating_over_time_labels,
        laserball_rating_over_time_data=laserball_rating_over_time_data,
    )

@app.post("/player")
async def player_post(request: Request) -> str:
    data = get_post(request)
    user = data["userid"]
    return response.redirect(f"/player/{user}")