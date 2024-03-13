from tortoise import Model, fields
from db.types import Team, Role

class LegacySM5Game(Model):
    id = fields.IntField(pk=True)
    winner = fields.CharEnumField(Team)
    players = fields.ManyToManyField("models.LegacySM5GamePlayer")
    timestamp = fields.DatetimeField(auto_now=True)

    def __str__(self) -> str:
        return f"LegacySM5Game()"
    
    def __repr__(self) -> str:
        return f"<LegacySM5Game>"
    
    async def get_red_players(self):
        return await self.players.filter(team=Team.RED)
    
    async def get_green_players(self):
        return await self.players.filter(team=Team.GREEN)

    
class LegacySM5GamePlayer(Model):
    player_dbid = fields.IntField()
    game_dbid = fields.IntField()
    team = fields.CharEnumField(Team)
    role = fields.CharEnumField(Role)
    score = fields.IntField()

class LegacyLaserballGame(Model):
    id = fields.IntField(pk=True)
    winner = fields.CharEnumField(Team)
    players = fields.ManyToManyField("models.LegacyLaserballGamePlayer")
    timestamp = fields.DatetimeField(auto_now=True)

    def __str__(self) -> str:
        return f"LegacyLaserballGame()"
    
    def __repr__(self) -> str:
        return f"<LegacyLaserballGame>"
    
    async def get_red_players(self):
        return await self.players.filter(team=Team.RED)
    
    async def get_blue_players(self):
        return await self.players.filter(team=Team.BLUE)

class LegacyLaserballGamePlayer(Model):
    player = fields.ForeignKeyField("models.Player")
    game = fields.ForeignKeyField("models.LegacyLaserballGame")
    team = fields.CharEnumField(Team)
    role = fields.CharEnumField(Role)
    goals = fields.IntField()
    assists = fields.IntField()
    steals = fields.IntField()
    clears = fields.IntField()
    blocks = fields.IntField()