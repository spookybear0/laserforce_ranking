from dataclasses import dataclass
from enum import Enum
from typing import List
from dataclasses_json import dataclass_json
from openskill import Rating


class Role(Enum):
    SCOUT = "scout"
    HEAVY = "heavy"
    COMMANDER = "commander"
    AMMO = "ammo"
    MEDIC = "medic"


class Team(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class Rank(Enum):
    UNRANKED = "unranked"
    IRON = "iron"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    DIAMOND = "diamond"
    IMMORTAL = "immortal"
    LASERMASTER = "lasermaster"


class RankMMR(Enum):
    UNRANKED = None
    IRON = 0.60
    BRONZE = 0.75
    SILVER = 1
    GOLD = 1.15
    DIAMOND = 1.25
    IMMORTAL = 1.35
    LASERMASTER = 2


@dataclass_json
@dataclass
class SM5GamePlayer:
    player_id: int
    game_id: int
    team: Team
    role: Role
    score: int
    adj_score: int = None


@dataclass_json
@dataclass
class LaserballGamePlayer:
    player_id: int
    game_id: int
    team: Team
    goals: int
    assists: int
    steals: int
    clears: int
    blocks: int


@dataclass_json
@dataclass
class Player:
    id: int
    player_id: str
    ipl_id: str
    codename: str
    sm5_rating: Rating
    laserball_rating: Rating
    game_player: SM5GamePlayer = None


@dataclass_json
@dataclass
class SM5_Game:
    id: int
    winner: Team
    date_logged: int
    players = []
    green = []
    red = []


@dataclass_json
@dataclass
class Laserball_Game:
    id: int
    winner: Team
    date_logged: int
    players = []
    blue = []
    red = []
