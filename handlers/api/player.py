from sanic import Request
from sanic import response

from db.player import Player
from helpers.statshelper import sentry_trace
from handlers.api import api_bp
from typing import Union, List, Dict, Any
from sanic_ext import openapi
from sanic_ext.extensions.openapi.definitions import RequestBody, Response
from db.types import Permission, IntRole
from textwrap import dedent

class PlayerSchema:
    player_id: str
    codename: str
    sm5_mu: float
    sm5_sigma: float
    laserball_mu: float
    laserball_sigma: float
    sm5_ordinal: int
    laserball_ordinal: int
    permissions: Permission
    entity_id: str

class PlayerSchemaWithStats(PlayerSchema):
    favorite_role: IntRole
    favorite_battlesuit: str
    shots_fired: int
    shots_hit: int
    win_percent: float
    sm5_win_percent: float
    laserball_win_percent: float
    median_role_score: List[float] # length 5

class PlayerSchemaWithRecentGames(PlayerSchemaWithStats):
    recent_sm5_games: List[Dict] # currently contains all player info/stats, but TODO: should just be game IDs
    recent_laserball_games: List[Dict] # currently contains all player info/stats, but TODO: should just be game IDs
    


@api_bp.post("/player/<identifier:str>")
@openapi.definition(
    summary="Get Player Information",
    description=dedent(
        """\
        Get information about a player by their codename, player ID, or RFID tag.
        If `stats` is true, include stats for the player.
        If `recent_games` is true, include recent games for the player.

        `identifier` can be the player's codename, player ID (ex: 4-43-1265), or an RFID tag (ex: 2831191 or 47:0f:51:b4).
        """
    ),
    response=[
        Response(
            # one of
            {"application/json": Union[PlayerSchema, PlayerSchemaWithStats, PlayerSchemaWithRecentGames]},
            description="Player information",
            status=200,
        ),
        Response(
            {"application/json": {"type": "object", "properties": {"error": {"type": "string"}}}},
            description="Player not found",
            status=404,
        ),
        Response(
            {"application/json": {"type": "object", "properties": {"error": {"type": "string"}}}},
            description="Invalid identifier",
            status=401,
        ),
    ],
    body=RequestBody(
        content={
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "stats": {"type": "boolean", "default": False},
                        "recent_games": {"type": "boolean", "default": False},
                    },
                }
            }
        }
    ),
)
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
            # get from rfid tag
            player = await Player.filter(tags__id=identifier.lower()).first()
            if player is None:
                return response.json({"error": "Player not found"}, status=404)

    return response.json(await player.to_dict(include_stats=stats, include_recent_games=recent_games))