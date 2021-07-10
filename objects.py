from dataclasses import dataclass
from enum import Enum

@dataclass
class Game:
    id: int
    player_id: str
    won: bool
    role: str
    score: int
    
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