from helpers.userhelper import get_median_role_score
from objects import GameType, Team
from utils import render_template, get_post
from helpers import gamehelper
from objects import Player
from shared import app
from sanic import Request, HTTPResponse, response, exceptions
from shared import app

sql = app.ctx.sql

@app.get("/player/<id>")
async def player_get(request: Request, id: str):

    player = await Player.from_player_id(id)

    if not player:
        player = await Player.from_name(id)  # could be codename

        if not player:
            raise exceptions.NotFound("Not found: Invalid ID or codename")

    print(await gamehelper.get_wins_player(GameType.SM5, Team.RED, player.player_id), await gamehelper.get_wins_player(GameType.SM5, Team.GREEN, player.player_id),)
    
    return await render_template(request, "player.html",
                                # general player info
                                player=player,
                                # player vs world bar in role plot
                                role_plot_data_player=await get_median_role_score(player),
                                role_plot_data_world=await get_median_role_score(),
                                # team rate pies (sm5/laserball)
                                red_teams_sm5=await gamehelper.get_teams(GameType.SM5, Team.RED, player.player_id),
                                green_teams_sm5=await gamehelper.get_teams(GameType.SM5, Team.GREEN, player.player_id),
                                red_teams_laserball=await gamehelper.get_teams(GameType.LASERBALL, Team.RED, player.player_id),
                                blue_teams_laserball=await gamehelper.get_teams(GameType.LASERBALL, Team.BLUE, player.player_id),
                                # win percents (sm5, laserball, all time)
                                sm5_win_percent=await gamehelper.get_win_percent(GameType.SM5, player.player_id),
                                laserball_win_percent=await gamehelper.get_win_percent(GameType.LASERBALL, player.player_id),
                                win_percent=await gamehelper.get_win_percent_overall(player.player_id),
                                # games won as team (sm5, laserball)
                                red_wins_sm5=await gamehelper.get_wins_player(GameType.SM5, Team.RED, player.player_id),
                                green_wins_sm5=await gamehelper.get_wins_player(GameType.SM5, Team.GREEN, player.player_id),
                                red_wins_laserball=await gamehelper.get_wins_player(GameType.LASERBALL, Team.RED, player.player_id),
                                blue_wins_laserball=await gamehelper.get_wins_player(GameType.LASERBALL, Team.BLUE, player.player_id),
                                )

@app.post("/player")
async def player_post(request: Request):
    data = get_post(request)
    user = data["userid"]
    return response.redirect(f"/player/{user}")