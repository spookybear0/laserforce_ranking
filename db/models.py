from typing import Any
from tortoise import Model, fields
from objects import Team, Role, GameType
from enum import Enum, IntEnum
import openskill

class EventType(IntEnum):
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

class IntRole(IntEnum):
    BASE = 0 # or no role
    COMMANDER = 1
    HEAVY = 2
    SCOUT = 3
    AMMO = 4
    MEDIC = 5


class Player(Model):
    id = fields.IntField(pk=True)
    player_id = fields.CharField(50)
    codename = fields.CharField(50)
    ipl_id = fields.CharField(50, default="")
    sm5_mu = fields.FloatField(default=25)
    sm5_sigma = fields.FloatField(default=8.333)
    laserball_mu = fields.FloatField(default=25)
    laserball_sigma = fields.FloatField(default=8.333)
    timestamp = fields.DatetimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.codename} ({self.player_id})"
    
    def __repr__(self) -> str:
        return f"<Player {self.codename} ({self.player_id})>"
    
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

class SM5Game(Model):
    id = fields.IntField(pk=True)
    winner = fields.CharEnumField(Team)
    tdf_name = fields.CharField(100)
    file_version = fields.CharField(20) # version is a decimal number, we can just store it as a string
    software_version = fields.CharField(20) # ditto ^
    arena = fields.CharField(20) # x-y, x=continent, y=arena (ex: 4-43)
    mission_type = fields.IntField() # no idea what this enum is
    mission_name = fields.CharField(100)
    start_time = fields.DatetimeField()
    mission_duration = fields.IntField() # in seconds
    log_time = fields.DatetimeField(auto_now_add=True)
    # there is a field in the tdf called "penatly", no idea what it is
    teams = fields.ManyToManyField("models.Teams")
    entity_starts = fields.ManyToManyField("models.EntityStarts")
    events = fields.ManyToManyField("models.Events")
    scores = fields.ManyToManyField("models.Scores")
    entity_ends = fields.ManyToManyField("models.EntityEnds")
    sm5_stats = fields.ManyToManyField("models.SM5Stats")


    def __str__(self) -> str:
        return f"SM5Game ({self.start_time})"
    
    def __repr__(self) -> str:
        return f"<SM5Game ({self.tdf_name})>"
    
    async def get_red_players(self):
        return await self.players.filter(team=Team.RED)
    
    async def get_green_players(self):
        return await self.players.filter(team=Team.GREEN)
    
class Teams(Model):
    index = fields.IntField()
    name = fields.CharField(50)
    color_enum = fields.IntField() # no idea what this enum is
    color_name = fields.CharField(50)

class EntityStarts(Model):
    time = fields.IntField() # time in milliseconds
    entity_id = fields.CharField(50, pk=True) # id of the entity
    type = fields.CharField(50) # can be [player, standard-target, maybe more]
    name = fields.CharField(75) # name of the entity
    team = fields.ForeignKeyField("models.Teams")
    level = fields.IntField() # for sm5 this is always 0
    role = fields.IntEnumField(IntRole) # 0 for targets, no idea what it is for laserball
    battlesuit = fields.CharField(50) # for targets its the target name

class Events(Model):
    time = fields.IntField() # time in milliseconds
    type = fields.IntEnumField(EventType)
    # variable number of fields depending on type of event
    # can be token or string for announcement
    # now make the field
    # TODO: maybe make this not a json field
    arguments = fields.JSONField()

class Scores(Model):
    time = fields.IntField() # time in milliseconds
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="entity_id")
    old = fields.IntField()
    delta = fields.IntField()
    new = fields.IntField()

class EntityEnds(Model):
    time = fields.IntField() # time in milliseconds
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="entity_id")
    type = fields.IntField() # don't know what enum this is
    score = fields.IntField()

class SM5Stats(Model):
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="entity_id")
    shots_hit = fields.IntField()
    shots_fired = fields.IntField()
    times_zapped = fields.IntField()
    times_missiled = fields.IntField()
    missile_hits = fields.IntField()
    nukes_detonated = fields.IntField()
    nukes_activated = fields.IntField()
    nuke_cancels = fields.IntField()
    medic_hits = fields.IntField()
    own_medic_hits = fields.IntField()
    medic_nukes = fields.IntField()
    scout_rapid_fires = fields.IntField()
    life_boosts = fields.IntField()
    ammo_boosts = fields.IntField()
    lives_left = fields.IntField()
    shots_left = fields.IntField()
    penalties = fields.IntField()
    shot_3_hits = fields.IntField()
    own_nuke_cancels = fields.IntField()
    shot_opponent = fields.IntField()
    shot_team = fields.IntField()
    missiled_opponent = fields.IntField()
    missiled_team = fields.IntField()


# legacy models
    
class LegacySM5Game(Model):
    id = fields.IntField(pk=True)
    winner = fields.CharEnumField(Team)
    players = fields.ManyToManyField("models.LegacySM5GamePlayer")
    timestamp = fields.DatetimeField(auto_now=True)

    def __str__(self) -> str:
        return f"LegacySM5Game()"
    
    def __repr__(self) -> str:
        return f"<LegacySM5Game"
    
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