from pyodide.http import pyfetch, FetchResponse
from typing import Optional, Any
from abc import ABC, abstractmethod
from enum import IntEnum

async def request(url: str, method: str = "GET", body: Optional[str] = None,
                  headers: Optional[dict[str, str]] = None, **fetch_kwargs: Any) -> FetchResponse:
    kwargs = {"method": method, "mode": "cors"}  # CORS: https://en.wikipedia.org/wiki/Cross-origin_resource_sharing
    if body and method not in ["GET", "HEAD"]:
        kwargs["body"] = body
    if headers:
        kwargs["headers"] = headers
    kwargs.update(fetch_kwargs)

    response = await pyfetch(url, **kwargs)
    return response

# role defaults

class RoleDefaults(ABC):
    name: str
    lives: int
    lives_resupply: int
    lives_max: int
    shots: int
    shots_resupply: int
    shots_max: int
    missiles: int


class CommanderDefaults:
    name = "commander"
    lives = 15
    lives_resupply = 4
    lives_max = 30
    shots = 30
    shots_resupply = 5
    shots_max = 60
    missiles = 5

class HeavyDefaults:
    name = "heavy"
    lives = 10
    lives_resupply = 3
    lives_max = 20
    shots = 20
    shots_resupply = 5
    shots_max = 40
    missiles = 5

class ScoutDefaults:
    name = "scout"
    lives = 15
    lives_resupply = 5
    lives_max = 30
    shots = 30
    shots_resupply = 10
    shots_max = 60
    missiles = 0

class AmmoDefaults:
    name = "ammo"
    lives = 10
    lives_resupply = 3
    lives_max = 20
    shots = 15
    shots_resupply = 0
    shots_max = 15
    missiles = 0

class MedicDefaults:
    name = "medic"
    lives = 20
    lives_resupply = 0
    lives_max = 20
    shots = 15
    shots_resupply = 5
    shots_max = 30
    missiles = 0

class EventType(IntEnum):
    # basic and sm5 events
    MISSION_START = 100
    MISSION_END = 101
    SHOT_EMPTY = 200 # unused?
    MISS = 201
    MISS_BASE = 202
    HIT_BASE = 203
    DESTROY_BASE = 204
    DAMAGED_OPPONENT = 205
    DOWNED_OPPONENT = 206
    DAMANGED_TEAM = 207 # unused?
    DOWNED_TEAM = 208 # unused?
    LOCKING = 300 # (aka missile start)
    MISSILE_BASE_MISS = 301
    MISSILE_BASE_DAMAGE = 302
    MISISLE_BASE_DESTROY = 303
    MISSILE_MISS = 304
    MISSILE_DAMAGE_OPPONENT = 305 # unused? theres no way for a missile to not down/destroy
    MISSILE_DOWN_OPPONENT = 306
    MISSILE_DAMAGE_TEAM = 307 # unused? ditto
    MISSILE_DOWN_TEAM = 308
    ACTIVATE_RAPID_FIRE = 400
    DEACTIVATE_RAPID_FIRE = 401 # unused?
    ACTIVATE_NUKE = 404
    DETONATE_NUKE = 405
    RESUPPLY_AMMO = 500
    RESUPPLY_LIVES = 502
    AMMO_BOOST = 510
    LIFE_BOOST = 512
    PENALTY = 600
    ACHIEVEMENT = 900
    BASE_AWARDED = 2819 # (technically #0B03 in hex)

    # laserball events

    PASS = 1100
    GOAL = 1101
    STEAL = 1103
    BLOCK = 1104
    ROUND_START = 1105
    ROUND_END = 1106
    GETS_BALL = 1107 # at the start of the round
    CLEAR = 1109