from sanic import Request
from helpers.statshelper import sentry_trace
from shared import app
from sanic.log import logger
from sanic import exceptions, response
from db.player import Player

@app.post("/api/player/<identifier:str>")
@sentry_trace
async def api_player(request: Request, identifier: str) -> str:
    # get information about the player

    stats = request.json.get("stats") # if true, return stats
    if stats is None:
        stats = False

    recent_games = request.json.get("recent_games")
    if recent_games is None:
        recent_games = False

    if identifier is None:
        return response.json({"error": "Invalid identifier"}, status=401)
    
    player = await Player.filter(codename=identifier).first()

    if player is None:
        player = await Player.filter(player_id=identifier).first()
        if player is None:
            return response.json({"error": "Player not found"}, status=404)
    
    return response.json(await player.to_dict(include_stats=stats, include_recent_games=recent_games))