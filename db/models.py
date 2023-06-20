from typing import Any
from tortoise import Model, fields, functions
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

    def __str__(self) -> str:
        names = {
            0: "Base",
            1: "Commander",
            2: "Heavy",
            3: "Scout",
            4: "Ammo",
            5: "Medic"
        }
        return names.get(self.value, "Base")


class Player(Model):
    id = fields.IntField(pk=True)
    player_id = fields.CharField(50, unique=True)
    codename = fields.CharField(50)
    ipl_id = fields.CharField(50, default="", unique=True)
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
    ranked = fields.BooleanField() # will this game affect player ratings and stats.
    ended_early = fields.BooleanField() # did the game end early?
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
    
    async def get_red_score(self):
        return sum(map(lambda x: x[0], await self.entity_ends.filter(entity__team__color_name="Fire").values_list("score")))
    
    async def get_green_score(self):
        return sum(map(lambda x: x[0], await self.entity_ends.filter(entity__team__color_name="Earth").values_list("score")))
    
    async def to_dict(self):
        # convert the entire game to a dict
        # this is used for the api
        final = {}

        final["id"] = self.id
        final["winner"] = self.winner.value
        final["tdf_name"] = self.tdf_name
        final["file_version"] = self.file_version
        final["software_version"] = self.software_version
        final["arena"] = self.arena
        final["mission_type"] = self.mission_type
        final["mission_name"] = self.mission_name
        final["start_time"] = str(self.start_time)
        final["mission_duration"] = self.mission_duration
        final["log_time"] = str(self.log_time)
        final["teams"] = [await (await team).to_dict() for team in await self.teams.all()]
        final["entity_starts"] = [await (await entity_start).to_dict() for entity_start in await self.entity_starts.all()]
        final["events"] = [await (await event).to_dict() for event in await self.events.all()]
        final["scores"] = [await (await score).to_dict() for score in await self.scores.all()]
        final["entity_ends"] = [await (await entity_end).to_dict() for entity_end in await self.entity_ends.all()]
        final["sm5_stats"] = [await (await sm5_stat).to_dict() for sm5_stat in await self.sm5_stats.all()]

        return final
    
class Teams(Model):
    index = fields.IntField()
    name = fields.CharField(50)
    color_enum = fields.IntField() # no idea what this enum is
    color_name = fields.CharField(50)

    @property
    def enum(self):
        conversions = {
            "Fire": Team.RED,
            "Earth": Team.GREEN,
            "Red": Team.RED,
            "Green": Team.GREEN
        }

        return conversions[self.color_name]

    async def to_dict(self):
        final = {}

        final["index"] = self.index
        final["name"] = self.name
        final["color_enum"] = int(self.color_enum)
        final["color_name"] = self.color_name

        return final

class EntityStarts(Model):
    id = fields.IntField(pk=True)
    time = fields.IntField() # time in milliseconds
    entity_id = fields.CharField(50) # id of the entity
    type = fields.CharField(50) # can be [player, standard-target, maybe more]
    name = fields.CharField(75) # name of the entity
    team = fields.ForeignKeyField("models.Teams")
    level = fields.IntField() # for sm5 this is always 0
    role = fields.IntEnumField(IntRole) # 0 for targets, no idea what it is for laserball
    battlesuit = fields.CharField(50) # for targets its the target name
    
    @property
    def player(self):
        # get the player object from the entity
        return Player.get(ipl_id=self.entity_id)

    async def to_dict(self):
        final = {}

        final["id"] = self.id
        final["time"] = self.time
        final["entity_id"] = self.entity_id
        final["type"] = self.type
        final["name"] = self.name
        final["team"] = (await self.team).index
        final["level"] = self.level
        final["role"] = int(self.role)
        final["battlesuit"] = self.battlesuit

        return final

class Events(Model):
    time = fields.IntField() # time in milliseconds
    type = fields.IntEnumField(EventType)
    # variable number of fields depending on type of event
    # can be token or string for announcement
    # now make the field
    # TODO: maybe make this not a json field
    arguments = fields.JSONField()

    async def to_dict(self):
        final = {}

        final["time"] = self.time
        final["type"] = int(self.type)
        final["arguments"] = self.arguments

        return final

class Scores(Model):
    time = fields.IntField() # time in milliseconds
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="id")
    old = fields.IntField()
    delta = fields.IntField()
    new = fields.IntField()

    async def to_dict(self):
        final = {}

        final["time"] = self.time
        final["entity"] = (await self.entity).entity_id
        final["old"] = self.old
        final["delta"] = self.delta
        final["new"] = self.new

        return final

class EntityEnds(Model):
    time = fields.IntField() # time in milliseconds
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="id")
    type = fields.IntField() # don't know what enum this is
    score = fields.IntField()
    current_rating_mu = fields.FloatField(null=True) # only for players, only for ranked games
    current_rating_sigma = fields.FloatField(null=True) # only for players, only for ranked games

    async def to_dict(self):
        final = {}

        final["time"] = self.time
        final["entity"] = (await self.entity).entity_id
        final["type"] = self.type
        final["score"] = self.score
        final["rating_change_mu"] = self.rating_change_mu
        final["rating_change_sigma"] = self.rating_change_sigma

        return final

class SM5Stats(Model):
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="id")
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

    async def to_dict(self):
        final = {}

        final["entity"] = (await self.entity).entity_id
        final["shots_hit"] = self.shots_hit
        final["shots_fired"] = self.shots_fired
        final["times_zapped"] = self.times_zapped
        final["times_missiled"] = self.times_missiled
        final["missile_hits"] = self.missile_hits
        final["nukes_detonated"] = self.nukes_detonated
        final["nukes_activated"] = self.nukes_activated
        final["nuke_cancels"] = self.nuke_cancels
        final["medic_hits"] = self.medic_hits
        final["own_medic_hits"] = self.own_medic_hits
        final["medic_nukes"] = self.medic_nukes
        final["scout_rapid_fires"] = self.scout_rapid_fires
        final["life_boosts"] = self.life_boosts
        final["ammo_boosts"] = self.ammo_boosts
        final["lives_left"] = self.lives_left
        final["shots_left"] = self.shots_left
        final["penalties"] = self.penalties
        final["shot_3_hits"] = self.shot_3_hits
        final["own_nuke_cancels"] = self.own_nuke_cancels
        final["shot_opponent"] = self.shot_opponent
        final["shot_team"] = self.shot_team
        final["missiled_opponent"] = self.missiled_opponent
        final["missiled_team"] = self.missiled_team

        return final

# legacy models
    
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