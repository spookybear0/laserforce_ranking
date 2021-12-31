from dataclasses import dataclass
from enum import Enum
from typing import List
from dataclasses_json import dataclass_json

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
    IRON = 0.60
    BRONZE = 0.75
    SILVER = 1
    GOLD = 1.15
    DIAMOND = 1.25
    IMMORTAL = 1.35
    LASERMASTER = 2

@dataclass_json
@dataclass
class GamePlayer:
    player_id: int
    game_id: int
    team: Team
    role: Role
    score: int
    adj_score: int=None

@dataclass_json  
@dataclass
class Player:
    id: int
    player_id: str
    ipl_id: str
    codename: str
    elo: int
    rank: str
    game_player: GamePlayer=None
    ranking_scout: float=0.0
    ranking_heavy: float=0.0
    ranking_commander: float=0.0
    ranking_medic: float=0.0
    ranking_ammo: float=0.0

@dataclass_json
@dataclass
class SM5_Game:
    id: int
    winner: Team
    date_logged: str=""
    players=[]
    green=[]
    red=[]
    
@dataclass_json
@dataclass
class Laserball_Game:
    id: int
    winner: Team
    date_logged: str=""
    players=[]
    blue=[]
    red=[]