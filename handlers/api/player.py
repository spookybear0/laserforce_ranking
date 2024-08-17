from sanic import Request
from sanic import response

from db.player import Player
from helpers.statshelper import sentry_trace
from shared import app
from typing import Union


@app.post("/api/player/<identifier:str>")
@sentry_trace
async def api_player(request: Request, identifier: Union[str, int]) -> str:
    # get information about the player

    stats = request.json.get("stats")  # if true, return stats
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
            try:
                rfid_tag = int(identifier)
            except ValueError:
                return response.json({"error": "Player not found"}, status=404)
            # get from rfid_tags
            player = await Player.filter(rfid_tags__contains=[rfid_tag]).first()
            if player is None:
                return response.json({"error": "Player not found"}, status=404)

    return response.json(await player.to_dict(include_stats=stats, include_recent_games=recent_games))