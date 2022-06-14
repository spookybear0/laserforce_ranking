from enum import Enum
from dataclasses import dataclass
from shared import sql
import datetime
import openskill

ALL_ROLES = ("scout", "heavy", "commander", "medic", "ammo")

class Team(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    
class Role(Enum):
    SCOUT = "scout"
    HEAVY = "heavy"
    COMMANDER = "commander"
    MEDIC = "medic"
    AMMO = "ammo"
    
class GameType(Enum):
    SM5 = "sm5"
    LASERBALL = "laserball"
    
@dataclass
class Player:
    id: int
    player_id: str
    ipl_id: str
    codename: str
    sm5_mu: float
    sm5_sigma: float
    laserball_mu: float
    laserball_sigma: float
    games: int
    goals: int = 0
    assists: int = 0
    steals: int = 0
    clears: int = 0
    blocks: int = 0
    timestamp: datetime.datetime = datetime.datetime.now()
    game_player = None
    
    async def _set_lifetime_stats(self):
        data = await sql.fetchone("SELECT SUM(goals), SUM(assists), SUM(steals), SUM(clears), SUM(blocks) FROM laserball_game_players WHERE player_id = %s", (self.player_id,))
        self.goals   = int(data[0])
        self.assists = int(data[1])
        self.steals  = int(data[2])
        self.clears  = int(data[3])
        self.blocks  = int(data[4])
    
    @classmethod
    async def from_id(cls, id: int):
        data = await sql.fetchall("SELECT * FROM players WHERE id = %s", (id,))
        ret = cls(*data)
        await ret._set_lifetime_stats()
        return ret

    @classmethod
    async def from_playerid(cls, name: str):
        data = await sql.fetchone("SELECT * FROM players WHERE player_id = %s", (name,))
        ret = cls(*data)
        await ret._set_lifetime_stats()
        return ret
    
    @classmethod
    async def from_name(cls, name: str):
        data = await sql.fetchone("SELECT * FROM players WHERE codename = %s", (name,))
        ret = cls(*data)
        await ret._set_lifetime_stats()
        print(ret)
        return ret
    
@dataclass
class SM5GamePlayer:
    player_id: int
    game_id: int
    team: Team
    role: Role
    score: int


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
    
@dataclass
class Game:
    id: int
    winner: Team
    type: GameType
    tdf: str = None
    timestamp: datetime.datetime = datetime.datetime.now()
    players = []
    green = []
    red = []
    blue = []
    
    @classmethod
    async def from_id(cls, id: int):
        data = await sql.fetchall("SELECT * FROM games WHERE id = %s", (id,))
        return cls(*data)