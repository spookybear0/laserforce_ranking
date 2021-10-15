from dataclasses import dataclass
from enum import Enum
from typing import List
    
class Role(Enum):
    SCOUT = "scout"
    HEAVY = "heavy"
    COMMANDER = "commander"
    AMMO = "ammo"
    MEDIC = "medic"
    
class Team(Enum):
    RED = "red"
    GREEN = "green"

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
    IRON = 0.75
    BRONZE = 0.85
    SILVER = 1
    GOLD = 1.15
    DIAMOND = 1.25
    IMMORTAL = 1.35
    LASERMASTER = 2
    
@dataclass
class Player:
    id: int
    player_id: str
    codename: str
    
@dataclass
class GamePlayer:
    player_id: int
    game_id: int
    team: Team
    role: Role
    score: int
    
@dataclass
class Game:
    id: int
    winner: Team
    players=[]