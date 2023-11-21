from enum import Enum
from typing import List
from laserforce import Player as IPLPlayer
from dataclasses import dataclass
import datetime
import openskill
import sys

def in_ipynb():
    return "ipykernel" in sys.modules

# not in juptyer notebook
if not in_ipynb():
    from shared import app
    sql = app.ctx.sql


ALL_ROLES = ("scout", "heavy", "commander", "medic", "ammo")

class Team(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

    def standardize(self):
        return self.value.capitalize()
    
class Role(Enum):
    SCOUT = "scout"
    HEAVY = "heavy"
    COMMANDER = "commander"
    MEDIC = "medic"
    AMMO = "ammo"
    
class GameType(Enum):
    SM5 = "sm5"
    LASERBALL = "laserball"

# DEPRECATED
# all of these are deprecated

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
    goals: int = 0
    assists: int = 0
    steals: int = 0
    clears: int = 0
    blocks: int = 0
    timestamp: datetime.datetime = datetime.datetime.now()
    game_player = None
    
    @property
    def sm5_ordinal(self):
        return self.sm5_mu - 3 * self.sm5_sigma
    
    @property
    def laserball_ordinal(self):
        return self.laserball_mu - 3 * self.laserball_sigma
    
    @property
    def sm5_rating(self):
        return openskill.Rating(self.sm5_mu, self.sm5_sigma)
    
    @property
    def laserball_rating(self):
        return openskill.Rating(self.laserball_mu, self.laserball_sigma)

    @property
    def games(self) -> int:
        return IPLPlayer.from_id(self.player_id).games

    async def _get_lifetime_stats(self):
        data = await sql.fetchone("SELECT SUM(goals), SUM(assists), SUM(steals), SUM(clears), SUM(blocks) FROM laserball_game_players WHERE player_id = %s", (self.player_id,))
        self.goals   = int(data[0]) if data[0] else 0
        self.assists = int(data[1]) if data[1] else 0
        self.steals  = int(data[2]) if data[2] else 0
        self.clears  = int(data[3]) if data[3] else 0
        self.blocks  = int(data[4]) if data[4] else 0
    
    @classmethod
    async def from_id(cls, id: int):
        data = await sql.fetchone("SELECT * FROM players WHERE id = %s", (id,))
        if not data:
            return None
        ret = cls(*data)
        await ret._get_lifetime_stats()
        return ret

    @classmethod
    async def from_player_id(cls, player_id: str):
        data = await sql.fetchone("SELECT * FROM players WHERE player_id = %s", (player_id,))
        if not data:
            return None
        ret = cls(*data)
        await ret._get_lifetime_stats()
        return ret
    
    @classmethod
    async def from_name(cls, name: str):
        data = await sql.fetchone("SELECT * FROM players WHERE codename = %s", (name,))
        if not data:
            return None
        ret = cls(*data)
        await ret._get_lifetime_stats()
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

    async def _get_game_players_team(self, team: Team) -> List[SM5GamePlayer]:
        q = await sql.fetchall(
            f"SELECT * FROM {self.type.value}_game_players WHERE `game_id` = %s AND `team` = %s",
            (self.id, team.value),
        )
        final = []

        if self.type == GameType.SM5:
            for game_player in q:
                if game_player[0] == "":
                    player = Player(0, "", "", "", 25, 8.333, 25, 8.333)
                else:
                    player = await Player.from_player_id(game_player[0])

                player.game_player = SM5GamePlayer(game_player[0], game_player[1], Team(game_player[2]),
                                                   Role(game_player[3]), game_player[4])

                final.append(player)
        elif self.type == GameType.LASERBALL:
            for game_player in q:
                if game_player[0] == "":
                    player = Player(0, "", "", "", 25, 8.333, 25, 8.333)
                else:
                    player = await Player.from_player_id(game_player[0])

                player.game_player = LaserballGamePlayer(game_player[0], game_player[1], Team(game_player[2]),
                                                        game_player[3], game_player[4], game_player[5],
                                                        game_player[6], game_player[7])
                final.append(player)
        return final

    async def _set_game_players(self):
        self.red = await self._get_game_players_team(Team.RED)

        if self.type == GameType.SM5:
            self.green = await self._get_game_players_team(Team.GREEN)
            self.players = [*self.red, *self.green]
        elif self.type == GameType.LASERBALL:
            self.blue = await self._get_game_players_team(Team.BLUE)
            self.players = [*self.red, *self.blue]

    async def _reload_elo(self):
        for player in [*self.players, *self.red, *self.green, *self.blue]:
            if player.player_id == "":
                continue
            if self.type == GameType.SM5:
                player.sm5_mu, player.sm5_sigma = await sql.fetchone("SELECT sm5_mu, sm5_sigma FROM players WHERE player_id = %s", (player.player_id,))
            elif self.type == GameType.LASERBALL:
                player.laserball_mu, player.laserball_sigma = await sql.fetchone("SELECT laserball_mu, laserball_sigma FROM players WHERE player_id = %s", (player.player_id,))

    def get_team_score(self, team: Team) -> int:
        if self.type == GameType.SM5:
            return sum([player.game_player.score for player in self.players if player.game_player.team == team])
        elif self.type == GameType.LASERBALL:
            return sum([player.game_player.goals for player in self.players if player.game_player.team == team])

    @classmethod
    async def from_id(cls, id: int):
        data = await sql.fetchone("SELECT * FROM games WHERE id = %s", (id,))
        if not data:
            return None
        game = cls(*data)

        game.type = GameType(game.type)
        game.winner = Team(game.winner)

        await game._set_game_players()

        return game