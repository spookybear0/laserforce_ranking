import sys
import os

dir_path = os.path.abspath("..")

if dir_path not in sys.path:
    sys.path.append(dir_path)

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/..")

import bar_chart_race as bcr
import pandas as pd
from config import config
from enum import Enum
import mysql.connector
import datetime
import asyncio
import openskill
from dataclasses import dataclass
import warnings
warnings.filterwarnings("ignore")

class Team(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

class GameType(Enum):
    SM5 = "sm5"
    LASERBALL = "laserball"
    
class Role(Enum):
    SCOUT = "scout"
    HEAVY = "heavy"
    COMMANDER = "commander"
    MEDIC = "medic"
    AMMO = "ammo"

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
        cursor = mydb.cursor()
        cursor.execute("SELECT SUM(goals), SUM(assists), SUM(steals), SUM(clears), SUM(blocks) FROM laserball_game_players WHERE player_id = %s", (self.player_id,))
        data = cursor.fetchone()
        self.goals   = int(data[0]) if data[0] else 0
        self.assists = int(data[1]) if data[1] else 0
        self.steals  = int(data[2]) if data[2] else 0
        self.clears  = int(data[3]) if data[3] else 0
        self.blocks  = int(data[4]) if data[4] else 0
    
    @classmethod
    async def from_id(cls, id: int):
        cursor = mydb.cursor()
        cursor.execute("SELECT * FROM players WHERE id = %s", (id,))
        data = cursor.fetchone()
        if not data:
            return None
        ret = cls(*data)
        await ret._get_lifetime_stats()
        return ret

    @classmethod
    async def from_player_id(cls, player_id: str):
        cursor = mydb.cursor()
        cursor.execute("SELECT * FROM players WHERE player_id = %s", (player_id,))
        data = cursor.fetchone()
        if not data:
            return None
        ret = cls(*data)
        await ret._get_lifetime_stats()
        return ret
    
    @classmethod
    async def from_name(cls, name: str):
        cursor = mydb.cursor()
        cursor.execute("SELECT * FROM players WHERE codename = %s", (name,))
        data = cursor.fetchone()
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

    async def _set_game_players(self):
        self.red = await self._get_game_players_team(Team.RED)

        if self.type == GameType.SM5:
            self.green = await self._get_game_players_team(Team.GREEN)
            self.players = [*self.red, *self.green]
        elif self.type == GameType.LASERBALL:
            self.blue = await self._get_game_players_team(Team.BLUE)
            self.players = [*self.red, *self.blue]

    async def _get_game_players_team(self, team: Team):
        cursor = mydb.cursor()
        cursor.execute(f"SELECT * FROM {self.type.value}_game_players WHERE `game_id` = %s AND `team` = %s", (self.id, team.value),)
        q = cursor.fetchall()
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
        return final

    #async def _reload_elo(self):
    #    for player in [*self.players, *self.red, *self.green, *self.blue]:
    #        if self.type == GameType.SM5:
    #            player.sm5_mu, player.sm5_sigma = await sql.fetchone("SELECT sm5_mu, sm5_sigma FROM players WHERE player_id = %s", (player.player_id,))
    #        elif self.type == GameType.LASERBALL:
    #            player.laserball_mu, player.laserball_sigma = await sql.fetchone("SELECT laserball_mu, laserball_sigma FROM players WHERE player_id = %s", (player.player_id,))

mydb = mysql.connector.connect(
    host=config["db_host"],
    user=config["db_user"],
    password=config["db_password"],
    port=config["db_port"],
    database=config["db_database"]
)

async def get_players():
    cursor = mydb.cursor()
    cursor.execute("SELECT codename FROM players")
    q = cursor.fetchall()
    final = []
    for player in q:
        final.append(player[0])
    return final

data = {}
all_players = []

for player in asyncio.run(get_players()):
    all_players.append(player)
    data[player] = []

i = 0

def attrgetter(obj, func):
    ret = []
    for i in obj:
        if callable(func):
            ret.append(func(i))
        elif isinstance(func, int):
            ret.append(i[func])
        else:
            ret.append(getattr(i, func))
    return ret

async def update_elo(game: Game, mode: GameType):
    mode = mode.value.lower()
    
    winner = game.winner
    
    team1 = game.red
    team1_mu = attrgetter(game.red, f"{mode}_mu")
    team1_sigma = attrgetter(game.red, f"{mode}_sigma")
    
    if mode == "sm5":
        team2 = game.green
        team2_mu = attrgetter(game.green, f"{mode}_mu")
        team2_sigma = attrgetter(game.green, f"{mode}_sigma")
    else: # laserball
        team2 = game.blue
        team2_mu = attrgetter(game.blue, f"{mode}_mu")
        team2_sigma = attrgetter(game.blue, f"{mode}_sigma")
    
    # convert to Rating
    team1_rating = []
    for i in range(len(team1)):
        team1_rating.append(openskill.Rating(team1_mu[i], team1_sigma[i]))
    
    team2_rating = []
    for i in range(len(team2)):
        team2_rating.append(openskill.Rating(team2_mu[i], team2_sigma[i]))

    if winner == Team.RED:  # red won
        team1_rating, team2_rating = openskill.rate([team1_rating, team2_rating])
    else:  # green/blue won
        team2_rating, team1_rating = openskill.rate([team2_rating, team1_rating])

    # convert back to Player 
    for i, p in enumerate(team1):
        setattr(p, f"{mode}_mu", team1_rating[i].mu)
        setattr(p, f"{mode}_sigma", team1_rating[i].sigma)
        
    for i, p in enumerate(team2):
        setattr(p, f"{mode}_mu", team2_rating[i].mu)
        setattr(p, f"{mode}_sigma", team2_rating[i].sigma)

    return (team1, team2)

async def update_game_elo(game):
    global df
    # gets id of the inserted game
    
    game.red, game.green = await update_elo(game, GameType.SM5)
    game.players = [*game.red, *game.green]

    # update openskill

    players = all_players.copy()
    
    for player in game.players:
        #print("\n1", player.codename, "\n2", player.sm5_mu * 3 * player.sm5_sigma, "\n3", df[player.codename], "\n4", pd.Series([player.sm5_mu * 3 * player.sm5_sigma]), "\n5", df[player.codename].append(pd.Series([player.sm5_mu * 3 * player.sm5_sigma])))
        if player.codename == "":
            continue # not logged in player
        players.remove(player.codename)
        data[player.codename].append(player.sm5_mu - 3 * player.sm5_sigma)

        # update rating
        #await sql.execute("""
        #    UPDATE players SET
        #    sm5_mu = %s,
        #    sm5_sigma = %s
        #    WHERE id = %s
        #""", (
        #    player.sm5_mu, player.sm5_sigma,
        #    player.id
        #))

    for player in players:
        if len(data[player]) == 0:
            data[player].append(0)
        else:
            data[player].append(data[player][-1])

async def get_all_games():
    games = []
    cursor = mydb.cursor()
    cursor.execute("SELECT COUNT(*) FROM games")
    count = cursor.fetchone()
    game_count = count[0]

    for id in range(1, game_count + 50):
        cursor.execute("SELECT * FROM games WHERE id = %s", (id,))
        data = cursor.fetchone()
        
        if not data:
            continue
        game = Game(*data)

        game.type = GameType(game.type)
        game.winner = Team(game.winner)

        await game._set_game_players()
        if game:
            games.append(game)
    
    return games

async def main():
    global data
    games = await get_all_games()
    i = 0

    for game in games:
        if game.type == GameType.SM5:
            await update_game_elo(game)
        i += 1

    data = {key:val for key, val in data.items() if val.count(0) != len(val)}

    print(len(data))

    df = pd.DataFrame(data=data)

    print(df)

    bcr.bar_chart_race(df=df, filename="out.mp4", title="SM5 players at ILT skill rating over time", n_bars=20, period_fmt="Game {int(x)}")

asyncio.run(main())

#print(bcr.load_dataset('covid19_tutorial'))