from dataclasses import dataclass
from enum import Enum
from typing import List
    
@dataclass
class Player:
    id: int
    player_id: str
    codename: str
    
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
    
@dataclass(init=False)
class Game:
    def __init__(self, id=0, player_id="", won=False, role=None, score=0, my_team=None, green_players=[], red_players=[]) -> None:
        self.id = id
        self.player_id = player_id
        self.won = won
        self.role = role
        self.score = score
        self.my_team = my_team
        self.green_players = green_players
        self.red_players = red_players
    
    id: int
    player_id: str
    won: bool
    role: Role
    score: int
    my_team: Team
    green_players: List[Player] # INCLUDES YOURSELF
    red_players: List[Player] # INCLUDES YOURSELF