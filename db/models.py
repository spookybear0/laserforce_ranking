from typing import List, Optional
from tortoise import Model, fields, functions
from tortoise.expressions import F, Q, Function
from objects import Team, Role, GameType
from enum import Enum, IntEnum
from collections import Counter
import openskill
import statistics
import bcrypt

class EventType(IntEnum):
    # basic and sm5 events
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

    # laserball events

    PASS = 1100
    GOAL = 1101
    STEAL = 1103
    BLOCK = 1104
    ROUND_START = 1105
    ROUND_END = 1106
    GETS_BALL = 1107 # at the start of the round
    CLEAR = 1109
    

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
    
    @classmethod
    def from_role(cls, role: Role) -> int:
        return cls({
            Role.COMMANDER: 1,
            Role.HEAVY: 2,
            Role.SCOUT: 3,
            Role.AMMO: 4,
            Role.MEDIC: 5
        }.get(role, 0))
    
    def to_role(self) -> Role:
        return {
            1: Role.COMMANDER,
            2: Role.HEAVY,
            3: Role.SCOUT,
            4: Role.AMMO,
            5: Role.MEDIC
        }.get(self.value)
    

class Permission(IntEnum):
    USER = 0
    ADMIN = 1

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

    # account stuff
    password = fields.CharField(100, null=True) # hashed password
    permissions = fields.IntEnumField(Permission, default=Permission.USER)
    
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
    
    # account stuff

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), self.password.encode("utf-8"))
    
    # stats
    
    async def get_favorite_role(self) -> Optional[Role]:
        """
        SM5 only
        """

        # get the most played role
        role = await EntityStarts.filter(entity_id=self.ipl_id).annotate(count=functions.Count("role")).order_by("-count").first()
        if role is None:
            return None
        return role.role
    
    async def get_favorite_battlesuit(self) -> Optional[str]:
        """
        SM5 only
        """

        # battlesuit is an entitystarts attribute which is a string
        # we need to count each time a battlesuit is used and return the most used one

        battlesuits = await EntityStarts.filter(entity_id=self.ipl_id).values_list("battlesuit", flat=True)

        if not battlesuits:
            return None
        
        # find most common battlesuit
        data = Counter(battlesuits)
        return data.most_common(1)[0][0]
    
    async def times_played_as_team(self, team: Team, game_type: GameType=None) -> int:
        """
        If game_type is None, all game types are counted
        """

        if team == Team.RED:
            team_color = "Fire"
        elif team == Team.BLUE:
            team_color = "Ice"
        else:
            team_color = "Earth"
            
        if game_type is None:
            return await EntityStarts.filter(entity_id=self.ipl_id, team__color_name=team_color).count()
        else:
            if game_type == GameType.SM5:
                return await EntityStarts.filter(entity_id=self.ipl_id, team__color_name=team_color, sm5games__mission_name__icontains="space marines").count()
            elif game_type == GameType.LASERBALL:
                return await EntityStarts.filter(entity_id=self.ipl_id, team__color_name=team_color, laserballgames__mission_name__icontains="laserball").count()
            
        
    async def times_played_as_role(self, role: Role) -> int:
        return await EntityStarts.filter(entity_id=self.ipl_id, role=IntRole.from_role(role)).count()
    
    async def get_win_percent(self, game_type: GameType=None) -> float:
        """
        If game_type is None, all game types are counted
        """

        if game_type is None:
            #return None

            wins = await EntityStarts.filter(entity_id=self.ipl_id, team__real_color_name=F("winner_color"), sm5games__winner__not_isnull="").count()
            losses = await EntityStarts.filter(entity_id=self.ipl_id).exclude(team=F("winner"), sm5games__winner__not_isnull="").count()
        else:
            game_type_filter_name = "space marines" if game_type == GameType.SM5 else "laserball"
            wins = await EntityStarts.filter(entity_id=self.ipl_id, team__real_color_name=F("winner_color"), sm5games__mission_name__icontains=game_type_filter_name).count()
            losses = await EntityStarts.filter(entity_id=self.ipl_id, sm5games__mission_name__icontains=game_type_filter_name).exclude(team=F("winner")).count()
    
        if wins + losses == 0:
            return 0
        
        return wins / (wins + losses)
    
    async def get_wins_as_team(self, team: Team, game_type: GameType=None) -> int:
        """
        If game_type is None, all game types are counted
        """

        if team == Team.RED:
            team_color = "Fire"
        elif team == Team.BLUE:
            team_color = "Ice"
        else:
            team_color = "Earth"
            
        if game_type is None:
            wins = await EntityStarts.filter(entity_id=self.ipl_id, team__real_color_name=F("winner_color"), sm5games__winner__not_isnull="").filter(team__color_name=team_color).count()
        else:
            if game_type == game_type.SM5:
                wins = await EntityStarts.filter(sm5games__mission_name__icontains="space marines", entity_id=self.ipl_id, team__real_color_name=F("winner_color")).filter(team__color_name=team_color).count()
            else: # laserball
                wins = await EntityStarts.filter(laserballgames__mission_name__icontains="laserball", entity_id=self.ipl_id, team__real_color_name=F("winner_color")).filter(team__color_name=team_color).count()
                print(wins)
        return wins
    
    # custom funcs for plotting
    
    async def get_median_role_score(self) -> List[float]:
        """
        SM5 only

        returns: roles median score in order of Role enum (Commander, Heavy, Scout, Ammo, Medic)
        """

        scores = []

        for role in range(1, 6):
            entities = await EntityStarts.filter(role=role, entity_id=self.ipl_id).values_list("id", flat=True)
            scores_role = await EntityEnds.filter(entity__id__in=entities).values_list("score", flat=True)
            try:
                scores.append(statistics.median(scores_role))
            except statistics.StatisticsError:
                scores.append(0)

        return scores
    
    @staticmethod
    async def get_median_role_score_world(median_role_score_player=None) -> List[float]:
        """
        SM5 only

        returns: roles median score in order of Role enum (Commander, Heavy, Scout, Ammo, Medic)

        we don't want to get median score for roles that haven't been played by the player
        """

        scores = []

        for role in range(1, 6):
            entities = await EntityStarts.filter(role=role).values_list("id", flat=True)
            scores_role = await EntityEnds.filter(entity__id__in=entities).values_list("score", flat=True)

            if median_role_score_player is not None:
                if median_role_score_player[role - 1] == 0:
                    continue

            try:
                scores.append(statistics.median(scores_role))
            except statistics.StatisticsError:
                scores.append(0)

        return scores

    def __str__(self) -> str:
        return f"{self.codename} ({self.player_id})"
    
    def __repr__(self) -> str:
        return f"<Player {self.codename} ({self.player_id})>"

class SM5Game(Model):
    id = fields.IntField(pk=True)
    winner = fields.CharEnumField(Team)
    winner_color = fields.CharField(20)
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
    # there is a field in the tdf called "penalty", no idea what it is
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
    
    async def get_entity_start_from_player(self, player: Player):
        return await self.entity_starts.filter(player=player).first()
    
    async def get_entity_start_from_token(self, token: str):
        return await self.entity_starts.filter(entity_id=token).first()
    
    async def get_entity_end_from_player(self, player: Player):
        return await self.entity_ends.filter(player=player).first()
    
    async def get_entity_end_from_token(self, token: str):
        return await self.entity_ends.filter(entity_id=token).first()
    
    async def get_entity_start_from_name(self, name: str):
        return await self.entity_starts.filter(name=name).first()
    
    async def get_entity_end_from_name(self, name: str):
        return await self.entity_ends.filter(entity__name=name).first()

    # funcs for getting total score at a certain time for a team
    
    async def get_red_score_at_time(self, time: int): # time in seconds
        return sum(map(lambda x: x[0], await self.scores.filter(time__lte=time, entity__team__color_name="Fire").values_list("delta")))

    async def get_green_score_at_time(self, time: int): # time in seconds
        return sum(map(lambda x: x[0], await self.scores.filter(time__lte=time, entity__team__color_name="Earth").values_list("delta")))
    
    # funcs for getting win chance and draw chance

    async def get_win_chance(self) -> List[float]:
        """
        Returns the win chance in the format [red, green]
        """
        # get the win chance for red team
        # this is based on the previous_elo of the player's entity_end

        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire")

        # get the previous elo for each player

        previous_elos_red = [openskill.Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma) for entity_end in entity_ends_red]

        # get all the entity_ends for the green team

        entity_ends_green = await self.entity_ends.filter(entity__team__color_name="Earth")

        # get the previous elo for each player

        previous_elos_green = [openskill.Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma) for entity_end in entity_ends_green]

        # get the win chance

        return openskill.predict_win([previous_elos_red, previous_elos_green])
    
    async def get_draw_chance(self) -> float:
        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire")

        # get the previous elo for each player

        previous_elos_red = [openskill.Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma) for entity_end in entity_ends_red]

        # get all the entity_ends for the green team

        entity_ends_green = await self.entity_ends.filter(entity__team__color_name="Earth")

        # get the previous elo for each player

        previous_elos_green = [openskill.Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma) for entity_end in entity_ends_green]

        # get the win chance

        return openskill.predict_draw([previous_elos_red, previous_elos_green])

    async def get_win_chance(self) -> List[float]:
        """
        Returns the win chance in the format [red, green]
        """
        # get the win chance for red team
        # this is based on the previous_elo of the player's entity_end

        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire")

        # get the previous elo for each player

        previous_elos_red = [openskill.Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma) for entity_end in entity_ends_red]

        # get all the entity_ends for the green team

        entity_ends_green = await self.entity_ends.filter(entity__team__color_name="Earth")

        # get the previous elo for each player

        previous_elos_green = [openskill.Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma) for entity_end in entity_ends_green]

        # get the win chance

        return openskill.predict_win([previous_elos_red, previous_elos_green])
    
    async def get_draw_chance(self) -> float:
        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire")

        # get the previous elo for each player

        previous_elos_red = [openskill.Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma) for entity_end in entity_ends_red]

        # get all the entity_ends for the green team

        entity_ends_green = await self.entity_ends.filter(entity__team__color_name="Earth")

        # get the previous elo for each player

        previous_elos_green = [openskill.Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma) for entity_end in entity_ends_green]

        # get the win chance

        return openskill.predict_draw([previous_elos_red, previous_elos_green])

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
    real_color_name = fields.CharField(50) # this isn't in the tdf, but it's useful for the api (ex: "Fire" -> "Red")

    @property
    def enum(self):
        conversions = {
            "Fire": Team.RED,
            "Earth": Team.GREEN,
            "Red": Team.RED,
            "Green": Team.GREEN,
            "Blue": Team.BLUE,
            "Ice": Team.BLUE,
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
    
    async def get_player(self) -> Player:
        # get the player object from the entity
        return await Player.get(ipl_id=self.entity_id)
    
    # UNTESTED
    async def get_entity_end(self) -> "EntityEnds":
        return await self.game.entity_ends.filter(entity_id=self.entity_id).first()
    
    # UNTESTED
    async def get_sm5_stats(self) -> "SM5Stats":
        return await self.game.sm5_stats.filter(entity_id=self.entity_id).first()
    
    # UNTESTED
    async def get_score(self) -> int:
        return (await self.get_entity_end()).score

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
    
    def __str__(self):
        return f"<EntityStarts id={self.id} entity_id={self.entity_id} type={self.type} name={self.name} team={self.team} level={self.level} role={self.role} battlesuit={self.battlesuit}>"

class Events(Model):
    time = fields.IntField() # time in milliseconds
    type = fields.IntEnumField(EventType)
    # variable number of fields depending on type of event
    # can be token or string for announcement
    # now make the field
    # TODO: maybe make this not a json field
    arguments = fields.JSONField() # list of arguments

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
    
    def __str__(self) -> str:
        return f"<Score {self.old} -> {self.new} ({self.delta})>"
    
    def __repr__(self) -> str:
        return str(self)

class EntityEnds(Model):
    time = fields.IntField() # time in milliseconds
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="id")
    type = fields.IntField() # don't know what enum this is
    score = fields.IntField()
    current_rating_mu = fields.FloatField(null=True) # only for players, only for ranked games
    current_rating_sigma = fields.FloatField(null=True) # only for players, only for ranked games
    previous_rating_mu = fields.FloatField(null=True) # only for players, only for ranked games
    previous_rating_sigma = fields.FloatField(null=True) # only for players, only for ranked games

    async def get_player(self) -> Player:
        # get the player object from the entity
        return await Player.get(ipl_id=self.entity_id)
    
    # UNTESTED
    async def get_entity_start(self) -> EntityStarts:
        return await self.game.entity_starts.filter(entity_id=self.entity_id).first()
    
    # UNTESTED
    async def get_sm5_stats(self) -> "SM5Stats":
        return await self.game.sm5_stats.filter(entity_id=self.entity_id).first()

    async def to_dict(self):
        final = {}

        final["time"] = self.time
        final["entity"] = (await self.entity).entity_id
        final["type"] = self.type
        final["score"] = self.score
        final["current_rating_mu"] = self.current_rating_mu
        final["current_rating_sigma"] = self.current_rating_sigma

        return final
    
    def __str__(self) -> str:
        return f"<EntityEnd {self.entity_id} {self.score}>"
    
    def __repr__(self) -> str:
        return str(self)

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

    
class LaserballGame(Model):
    id = fields.IntField(pk=True)
    winner = fields.CharEnumField(Team)
    winner_color = fields.CharField(20)
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
    laserball_stats = fields.ManyToManyField("models.LaserballStats")

    def __str__(self) -> str:
        return f"LaserballGame ({self.start_time})"
    
    def __repr__(self) -> str:
        return f"<LaserballGame ({self.tdf_name})>"
    
    async def get_red_score(self):
        return sum(map(lambda x: x[0], await self.entity_ends.filter(entity__team__color_name="Fire").values_list("score")))
    
    async def get_blue_score(self):
        return sum(map(lambda x: x[0], await self.entity_ends.filter(entity__team__color_name="Ice").values_list("score")))
    
    async def get_red_score_at_time(self, time):
        return sum(map(lambda x: x[0], await self.scores.filter(time__lte=time, entity__team__color_name="Fire").values_list("delta")))
    
    async def get_blue_score_at_time(self, time):
        return sum(map(lambda x: x[0], await self.scores.filter(time__lte=time, entity__team__color_name="Ice").values_list("delta")))
    
    async def get_rounds_at_time(self, time):
        return (await self.events.filter(time__lte=time, type=EventType.ROUND_END).count()) + 1
    
    # funcs for getting win chance and draw chance

    async def get_win_chance_at_time(self) -> List[float]:
        """
        Returns the win chance in the format [red, green]
        """
        # get the win chance for red team
        # this is based on the previous_elo of the player's entity_end

        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire")

        # get the previous elo for each player

        previous_elos_red = [openskill.Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma) for entity_end in entity_ends_red]

        # get all the entity_ends for the green team

        entity_ends_blue = await self.entity_ends.filter(entity__team__color_name="Ice")

        # get the previous elo for each player

        previous_elos_blue = [openskill.Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma) for entity_end in entity_ends_blue]

        # get the win chance

        return openskill.predict_win([previous_elos_red, previous_elos_blue])
    
    async def get_draw_chance_at_time(self) -> float:
        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire")

        # get the previous elo for each player

        previous_elos_red = [openskill.Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma) for entity_end in entity_ends_red]

        # get all the entity_ends for the green team

        entity_ends_blue = await self.entity_ends.filter(entity__team__color_name="Ice")

        # get the previous elo for each player

        previous_elos_blue = [openskill.Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma) for entity_end in entity_ends_blue]

        # get the win chance

        return openskill.predict_draw([previous_elos_red, previous_elos_blue])

    async def get_win_chance(self) -> List[float]:
        """
        Returns the win chance in the format [red, green]
        """
        # get the win chance for red team
        # this is based on the previous_elo of the player's entity_end

        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire")

        # get the previous elo for each player

        previous_elos_red = [openskill.Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma) for entity_end in entity_ends_red]

        # get all the entity_ends for the green team

        entity_ends_blue = await self.entity_ends.filter(entity__team__color_name="Ice")

        # get the previous elo for each player

        previous_elos_blue = [openskill.Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma) for entity_end in entity_ends_blue]

        # get the win chance

        return openskill.predict_win([previous_elos_red, previous_elos_blue])
    
    async def get_draw_chance(self) -> float:
        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire")

        # get the previous elo for each player

        previous_elos_red = [openskill.Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma) for entity_end in entity_ends_red]

        # get all the entity_ends for the green team

        entity_ends_blue = await self.entity_ends.filter(entity__team__color_name="Ice")

        # get the previous elo for each player

        previous_elos_blue = [openskill.Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma) for entity_end in entity_ends_blue]

        # get the win chance

        return openskill.predict_draw([previous_elos_red, previous_elos_blue])
    
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
        final["laserball_stats"] = [await (await laserball_stats).to_dict() for laserball_stats in await self.laserball_stats.all()]

        return final
    
class LaserballStats(Model):
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="id")
    goals = fields.IntField()
    assists = fields.IntField()
    passes = fields.IntField()
    steals = fields.IntField()
    clears = fields.IntField()
    blocks = fields.IntField()
    started_with_ball = fields.IntField()
    times_stolen = fields.IntField()
    times_blocked = fields.IntField()
    passes_received = fields.IntField()

    async def to_dict(self):
        final = {}

        final["entity"] = (await self.entity).entity_id
        final["goals"] = self.goals
        final["assists"] = self.assists
        final["passes"] = self.passes
        final["steals"] = self.steals
        final["clears"] = self.clears
        final["blocks"] = self.blocks
        final["started_with_ball"] = self.started_with_ball
        final["times_stolen"] = self.times_stolen
        final["times_blocked"] = self.times_blocked
        final["passes_received"] = self.passes_received

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