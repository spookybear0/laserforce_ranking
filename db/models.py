from dataclasses import dataclass
from typing import List, Optional
from tortoise import Model, fields, functions
from tortoise.expressions import F, Q
from objects import Team, Role, GameType
from enum import Enum, IntEnum
from collections import Counter
try:
    from openskill.models import PlackettLuceRating as Rating, PlackettLuce
except ImportError:
    from openskill.models.weng_lin.plackett_luce import PlackettLuceRating as Rating, PlackettLuce
import statistics
import bcrypt
import math
import sys

model = PlackettLuce()

def suffix(d):
    return {1:"st",2:"nd",3:"rd"}.get(d%20, "th")

def strftime_ordinal(format, t):
    return t.strftime(format).replace("{S}", str(t.day) + suffix(t.day))

class EventType(Enum):
    # basic and sm5 events
    MISSION_START = "0100"
    MISSION_END = "0101"
    SHOT_EMPTY = "0200" # unused?
    MISS = "0201"
    MISS_BASE = "0202"
    HIT_BASE = "0203"
    DESTROY_BASE = "0204"
    DAMAGED_OPPONENT = "0205"
    DOWNED_OPPONENT = "0206"
    DAMANGED_TEAM = "0207" # unused?
    DOWNED_TEAM = "0208" # unused?
    LOCKING = "0300" # (aka missile start)
    MISSILE_BASE_MISS = "0301"
    MISSILE_BASE_DAMAGE = "0302"
    MISISLE_BASE_DESTROY = "0303"
    MISSILE_MISS = "0304"
    MISSILE_DAMAGE_OPPONENT = "0305" # unused? theres no way for a missile to not down/destroy
    MISSILE_DOWN_OPPONENT = "0306"
    MISSILE_DAMAGE_TEAM = "0307" # unused?
    MISSILE_DOWN_TEAM = "0308"
    ACTIVATE_RAPID_FIRE = "0400"
    DEACTIVATE_RAPID_FIRE = "0401" # unused?
    ACTIVATE_NUKE = "0404"
    DETONATE_NUKE = "0405"
    RESUPPLY_AMMO = "0500"
    RESUPPLY_LIVES = "0502"
    AMMO_BOOST = "0510"
    LIFE_BOOST = "0512"
    PENALTY = "0600"
    ACHIEVEMENT = "0900"
    REWARD = "0902"
    BASE_AWARDED = "0B03" # (technically #0B03 in hex)

    # laserball events

    PASS = "1100"
    GOAL = "1101"
    ASSIST = "1102" # THIS IS NOT A REAL EVENT TYPE (as far as im aware, im generating it myself)
    STEAL = "1103"
    BLOCK = "1104"
    ROUND_START = "1105"
    ROUND_END = "1106"
    GETS_BALL = "1107" # at the start of the round
    TIME_VIOLATION = "1108"
    CLEAR = "1109"
    FAIL_CLEAR = "110A"
    

class IntRole(IntEnum):
    OTHER = 0 # or no role
    COMMANDER = 1
    HEAVY = 2
    SCOUT = 3
    AMMO = 4
    MEDIC = 5

    def __str__(self) -> str:
        names = {
            0: "Other",
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
    

class PlayerStateType(IntEnum):
    ACTIVE = 0
    UNKNOWN = 1 # unused?
    RESETTABLE = 2
    DOWN = 3

class Permission(IntEnum):
    USER = 0
    ADMIN = 1

@dataclass
class BallPossessionEvent:
    """This denotes a time at which an entity gains possession of the ball in Laserball."""
    timestamp_millis: int
    entity_id: Optional[str]

class Player(Model):
    id = fields.IntField(pk=True)
    player_id = fields.CharField(20)
    codename = fields.CharField(255)
    entity_id = fields.CharField(50, default="")
    sm5_mu = fields.FloatField(default=25)
    sm5_sigma = fields.FloatField(default=8.333)
    laserball_mu = fields.FloatField(default=25)
    laserball_sigma = fields.FloatField(default=8.333)
    timestamp = fields.DatetimeField(auto_now=True)

    # account stuff
    password = fields.CharField(255, null=True) # hashed password
    permissions = fields.IntEnumField(Permission, default=Permission.USER)
    
    @property
    def sm5_ordinal(self):
        return self.sm5_mu - 3 * self.sm5_sigma
    
    @property
    def laserball_ordinal(self):
        return self.laserball_mu - 3 * self.laserball_sigma
    
    @property
    def sm5_rating(self):
        return Rating(self.sm5_mu, self.sm5_sigma)

    @property
    def laserball_rating(self):
        return Rating(self.laserball_mu, self.laserball_sigma)
    
    # account stuff

    async def set_password(self, password: str) -> None:
        from helpers import userhelper
        self.password = userhelper.hash_password(password)
        await self.save()

    def check_password(self, password: Optional[str]) -> bool:
        if self.password is None or password is None:
            return False

        return bcrypt.checkpw(password.encode("utf-8"), self.password.encode("utf-8"))
    
    # stats
    
    async def get_favorite_role(self) -> Optional[Role]:
        """
        SM5 only
        """

        # get the most played role
        role = await EntityStarts.filter(entity_id=self.entity_id, sm5games__mission_name__icontains="space marines").annotate(count=functions.Count("role")).order_by("-count").first()
        if role is None:
            return None
        return role.role
    
    async def get_favorite_battlesuit(self, game_type: Optional[GameType]=None) -> Optional[str]:
        """
        Argument "game_type" can be None, "sm5", or "laserball"
        None means all game types are counted
        """

        # battlesuit is an entitystarts attribute which is a string
        # we need to count each time a battlesuit is used and return the most used one

        if game_type is None:
            battlesuits = await EntityStarts.filter(entity_id=self.entity_id).values_list("battlesuit", flat=True)
        elif game_type == GameType.SM5:
            battlesuits = await EntityStarts.filter(entity_id=self.entity_id, sm5games__mission_name__icontains="space marines").values_list("battlesuit", flat=True)
        elif game_type == GameType.LASERBALL:
            battlesuits = await EntityStarts.filter(entity_id=self.entity_id, laserballgames__mission_name__icontains="laserball").values_list("battlesuit", flat=True)
        else:
            # raise exception
            raise ValueError("Invalid game_type")

        if not battlesuits:
            return None
        
        # find most common battlesuit
        data = Counter(battlesuits)
        return data.most_common(1)[0][0]
    
    async def get_sean_hits(self, game_type: Optional[GameType]=None) -> int:
        """
        AIDAN REQUESTED THIS

        Argument "game_type" can be None, "sm5", or "laserball"
        None means all game types are counted

        returns: number of times the player hit sean (Commander)
        """

        sean_entity_id = "#w7Wt8y"

        if game_type is None:
            return await Events.filter(
                arguments__filter={"0": self.entity_id}
            ).filter(
                Q(arguments__filter={"1": " zaps "}) | Q(arguments__filter={"1": " blocks "}) | Q(arguments__filter={"1": " steals from "})
            ).filter(
                arguments__filter={"2": sean_entity_id}
            ).count()
        elif game_type == GameType.SM5:
            return await Events.filter(
                sm5games__mission_name__icontains="space marines", arguments__filter={"0": self.entity_id}
            ).filter(
                arguments__filter={"1": " zaps "}
            ).filter(
                arguments__filter={"2": sean_entity_id}
            ).count()
        elif game_type == GameType.LASERBALL:
            return await Events.filter(
            laserballgames__mission_name__icontains="laserball", arguments__filter={"0": self.entity_id}
            ).filter(
                Q(arguments__filter={"1": " blocks "}) | Q(arguments__filter={"1": " steals from "})
            ).filter(
                arguments__filter={"2": sean_entity_id}
            ).count()
        else:
            # raise exception
            raise ValueError("Invalid game_type")
    
    async def get_shots_fired(self, game_type: Optional[GameType]=None) -> int:
        """
        Argument "game_type" can be None, "sm5", or "laserball"
        None means all game types are counted

        returns: number of shots fired by the player
        """

        if game_type is None:
            return sum(await SM5Stats.filter(entity__entity_id=self.entity_id).values_list("shots_fired", flat=True) + await LaserballStats.filter(entity__entity_id=self.entity_id).values_list("shots_fired", flat=True))
        elif game_type == GameType.SM5:
            return sum(await SM5Stats.filter(entity__entity_id=self.entity_id).values_list("shots_fired", flat=True))
        elif game_type == GameType.LASERBALL:
            return sum(await LaserballStats.filter(entity__entity_id=self.entity_id).values_list("shots_fired", flat=True))
        
    async def get_shots_hit(self, game_type: Optional[GameType]=None) -> int:
        """
        Argument "game_type" can be None, "sm5", or "laserball"
        None means all game types are counted

        returns: number of shots hit by the player
        """

        if game_type is None:
            return sum(await SM5Stats.filter(entity__entity_id=self.entity_id).values_list("shots_hit", flat=True) + await LaserballStats.filter(entity__entity_id=self.entity_id).values_list("shots_hit", flat=True))
        elif game_type == GameType.SM5:
            return sum(await SM5Stats.filter(entity__entity_id=self.entity_id).values_list("shots_hit", flat=True))
        elif game_type == GameType.LASERBALL:
            return sum(await LaserballStats.filter(entity__entity_id=self.entity_id).values_list("shots_hit", flat=True))
    
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
            return await EntityStarts.filter(entity_id=self.entity_id, team__color_name=team_color).count()
        else:
            if game_type == GameType.SM5:
                return await EntityStarts.filter(entity_id=self.entity_id, team__color_name=team_color, sm5games__mission_name__icontains="space marines").count()
            elif game_type == GameType.LASERBALL:
                return await EntityStarts.filter(entity_id=self.entity_id, team__color_name=team_color, laserballgames__mission_name__icontains="laserball").count()
            
        
    async def times_played_as_role(self, role: Role) -> int:
        return await EntityStarts.filter(entity_id=self.entity_id, role=IntRole.from_role(role)).count()
    
    async def get_win_percent(self, game_type: GameType=None) -> float:
        """
        If game_type is None, all game types are counted
        """

        if game_type is None:
            #return None

            wins = await EntityStarts.filter(entity_id=self.entity_id, team__real_color_name=F("winner_color"), sm5games__winner__not_isnull="").count()
            losses = await EntityStarts.filter(entity_id=self.entity_id).exclude(team=F("winner"), sm5games__winner__not_isnull="").count()
        else:
            game_type_filter_name = "space marines" if game_type == GameType.SM5 else "laserball"
            wins = await EntityStarts.filter(entity_id=self.entity_id, team__real_color_name=F("winner_color"), sm5games__mission_name__icontains=game_type_filter_name).count()
            losses = await EntityStarts.filter(entity_id=self.entity_id, sm5games__mission_name__icontains=game_type_filter_name).exclude(team=F("winner")).count()
    
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
            wins = await EntityStarts.filter(entity_id=self.entity_id, team__real_color_name=F("winner_color"), sm5games__winner__not_isnull="").filter(team__color_name=team_color).count()
        else:
            if game_type == game_type.SM5:
                wins = await EntityStarts.filter(sm5games__mission_name__icontains="space marines", entity_id=self.entity_id, team__real_color_name=F("winner_color")).filter(team__color_name=team_color).count()
            else: # laserball
                wins = await EntityStarts.filter(laserballgames__mission_name__icontains="laserball", entity_id=self.entity_id, team__real_color_name=F("winner_color")).filter(team__color_name=team_color).count()
        return wins
    
    # custom funcs for plotting
    
    async def get_median_role_score(self) -> List[float]:
        """
        SM5 only

        returns: roles median score in order of Role enum (Commander, Heavy, Scout, Ammo, Medic)
        """

        scores = []

        for role in range(1, 6):
            entities = await EntityStarts.filter(role=role, entity_id=self.entity_id).values_list("id", flat=True)
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
    winner = fields.CharEnumField(Team, null=True) # null if the game ended early
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
    player_states = fields.ManyToManyField("models.PlayerStates")
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
        from helpers.ratinghelper import ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA

        # get the win chance for red team
        # this is based on the most current elo of the player's entity_end

        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire", entity__type="player")

        # get the elo for each player

        elos_red = []

        for entity_end in entity_ends_red:
            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                elos_red.append(Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA))
            else:
                player = await entity_end.get_player()
                elos_red.append(Rating(player.sm5_mu, player.sm5_sigma))

        # get all the entity_ends for the green team

        entity_ends_green = await self.entity_ends.filter(entity__team__color_name="Earth", entity__type="player")

        # get the elo for each player

        elos_green = []
        for entity_end in entity_ends_green:
            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                elos_green.append(Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA))
            else:
                player = await entity_end.get_player()
                elos_green.append(Rating(player.sm5_mu, player.sm5_sigma))

        # get the win chance

        return model.predict_win([elos_red, elos_green])
    
    async def get_win_chance_before_game(self) -> List[float]:
        """
        Returns the win chance as guessed before the game happened in the format [red, green]
        """
        from helpers.ratinghelper import ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA

        # get the win chance for red team
        # this is based on the previous_elo of the player's entity_end

        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire", entity__type="player")

        # get the previous elo for each player

        previous_elos_red = []

        for entity_end in entity_ends_red:
            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                previous_elos_red.append(Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA))
            else:
                previous_elos_red.append(Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma))

        # get all the entity_ends for the green team

        entity_ends_green = await self.entity_ends.filter(entity__team__color_name="Earth", entity__type="player")

        # get the previous elo for each player

        previous_elos_green = []
        for entity_end in entity_ends_green:
            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                previous_elos_green.append(Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA))
            else:
                previous_elos_green.append(Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma))

        # double check if elo is None or not
                
        for i, elo in enumerate(previous_elos_red + previous_elos_green):
            if elo is None or elo.mu is None or elo.sigma is None:
                if i < len(previous_elos_red):
                    previous_elos_red[i] = Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA)
                else:
                    previous_elos_green[i - len(previous_elos_red)] = Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA)

        # get the win chance

        return model.predict_win([previous_elos_red, previous_elos_green])
    
    async def get_win_chance_after_game(self) -> List[float]:
        """
        Returns the win chance as guessed **directly** after the game happened in the format [red, green]
        """
        from helpers.ratinghelper import ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA

        # get the win chance for red team
        # this is based on the current_elo of the player's entity_end

        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire", entity__type="player")

        # get the current_elo for each player

        current_elos_red = []

        for entity_end in entity_ends_red:
            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                current_elos_red.append(Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA))
            else:
                current_elos_red.append(Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma))

        # get all the entity_ends for the green team

        entity_ends_green = await self.entity_ends.filter(entity__team__color_name="Earth", entity__type="player")

        # get the current_elo for each player

        current_elos_green = []
        for entity_end in entity_ends_green:
            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                current_elos_green.append(Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA))
            else:
                current_elos_green.append(Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma))

        # double check if elo is None or not
                
        for i, elo in enumerate(current_elos_red + current_elos_green):
            if elo is None or elo.mu is None or elo.sigma is None:
                if i < len(current_elos_red):
                    current_elos_red[i] = Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA)
                else:
                    current_elos_green[i - len(current_elos_red)] = Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA)

        # get the win chance

        return model.predict_win([current_elos_red, current_elos_green])
    
    def get_timestamp(self, time_zone: str="America/Los_Angeles") -> str:
        """
        Returns the timestamp of the game in the specified time zone
        """

        # get zero pad modifier for os
        if sys.platform == "win32":
            zero_pad = "#"
        else:
            zero_pad = "-"

        return strftime_ordinal(f"%A, %B {'{S}'} at %{zero_pad}I:%M %p", self.start_time)
    
    async def get_battlesuits(self) -> List[str]: # only the non-member players
        """
        Returns a list of entity_starts of battlesuits used in the game
        """

        return await self.entity_starts.filter(type="player", entity_id__startswith="@")
    
    async def get_players(self) -> List[str]: # all players
        """
        Returns a list of entity_starts of players in the game
        """

        return await self.entity_starts.filter(type="player")
    
    async def get_previous_game_id(self) -> Optional[int]:
        """
        Returns the game id of the previous game
        """
        
        id_ = await SM5Game.filter(start_time__lt=self.start_time).order_by("-start_time").values_list("id", flat=True)
        if not id_:
            return None
        return id_[0]

    async def get_next_game_id(self) -> Optional[int]:
        """
        Returns the game id of the next game
        """

        id_ = await SM5Game.filter(start_time__gt=self.start_time).order_by("start_time").values_list("id", flat=True)
        if not id_:
            return None
        return id_[0]

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
    member_id = fields.CharField(50, null=True) # only for newer games (or ones with the option to include member_id)
    
    async def get_player(self) -> Player:
        # get the player object from the entity
        return await Player.get(entity_id=self.entity_id)
    
    async def get_entity_end(self) -> "EntityEnds":
        return await EntityEnds.filter(entity__id=self.id).first()
    
    async def get_sm5_stats(self) -> "SM5Stats":
        return await SM5Stats.filter(entity__id=self.id).first()
    
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
        final["member_id"] = self.member_id

        return final
    
    def __str__(self):
        return f"<EntityStarts id={self.id} entity_id={self.entity_id} type={self.type} name={self.name} team={self.team} level={self.level} role={self.role} battlesuit={self.battlesuit} member_id={self.member_id}>"

class Events(Model):
    time = fields.IntField() # time in milliseconds
    type = fields.CharEnumField(EventType)
    # variable number of fields depending on type of event
    # can be token or string for announcement
    # now make the field
    # TODO: maybe make this not a json field
    arguments = fields.JSONField() # list of arguments

    async def to_dict(self):
        final = {}

        final["time"] = self.time
        final["type"] = self.type.value
        final["arguments"] = self.arguments

        return final
    
class PlayerStates(Model):
    time = fields.IntField() # time in milliseconds
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="id")
    state = fields.IntEnumField(PlayerStateType)

    async def to_dict(self):
        final = {}

        final["time"] = self.time
        final["entity"] = (await self.entity).entity_id
        final["state"] = self.state

        return final

class Scores(Model):
    time = fields.IntField() # time in milliseconds
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="id")
    old = fields.IntField() # old score
    delta = fields.IntField() # change in score
    new = fields.IntField() # new score

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
        return await Player.get(entity_id=(await self.entity).entity_id)
    
    async def get_entity_start(self) -> EntityStarts:
        return await self.entity
    
    async def get_sm5_stats(self) -> "SM5Stats":
        return SM5Stats.filter(entity__id=self.id).first()

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
        return f"<EntityEnd {self.entity_id} score={self.score}>"
    
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

    async def mvp_points(self) -> float:
        """
        mvp points according to lfstats.com

        NOTE: this is a function, while LaserballStats.mvp_points is a property

        CAUTION: not completely accurate due to elimation points not being implemented
        """

        score = await (await self.entity).get_score()

        total_points = 0

        # accuracy: .1 point for every 1% of accuracy, rounded up

        accuracy = (self.shots_hit / self.shots_fired) if self.shots_fired != 0 else 0
        total_points += math.ceil(accuracy * 10)

        # medic hits: 1 point for every medic hit, -1 for your own medic hits

        total_points += self.medic_hits - self.own_medic_hits

        # elims: minimum 1 point if your team eliminates the other team, increased by 1/60 for each of second of game time remaining above 1 minute.

        # TODO: implement this

        # cancel opponent nukes: 3 points for every opponent nuke canceled

        total_points += self.nuke_cancels * 3

        # cancel own nukes: -3 points for every own nuke canceled

        total_points -= self.own_nuke_cancels * 3

        # get missiled: -1 point for every time you get missiled

        total_points -= self.times_missiled

        # get eliminated: -1 point for getting elimated (doesn't apply to medics)

        if self.lives_left <= 0 and (await self.entity).role != IntRole.MEDIC:
            total_points -= 1

        # commander specific points:

        if (await self.entity).role == IntRole.COMMANDER:
            # missile opponent: 1 point for every missile on an opponent

            total_points += self.missiled_opponent

            # nukes: 1 point for every nuke detonated

            total_points += self.nukes_detonated

            # nukes canceled: -1 point for every nuke that you activated that was canceled

            total_points -= self.own_nuke_cancels

            # score bonus: 1 point (fractionally) for every 1000 points of score over 10000

            if score > 10000:
                total_points += (score - 10000) / 1000

        # heavy specific points:
        elif (await self.entity).role == IntRole.HEAVY:
            # missiles: 2 points for every missile hit

            total_points += self.missiled_opponent * 2

            # score bonus: 1 point (fractionally) for every 1000 points of score over 7000

            if score > 7000:
                total_points += (score - 7000) / 1000

        # scout specific points:
        elif (await self.entity).role == IntRole.SCOUT:
            # hits vs 3 hit (commander/heavy): .2 points for every hit vs 3 hit

            total_points += self.shot_3_hits * .2

            # score bonus: 1 point (fractionally) for every 1000 points of score over 6000

            if score > 6000:
                total_points += (score - 6000) / 1000

        # ammo specific points:
        elif (await self.entity).role == IntRole.AMMO:
            # ammo boosts: 3 point for every ammo boost

            total_points += self.ammo_boosts * 3

            # score bonus: 1 point (fractionally) for every 1000 points of score over 5000

            if score > 3000:
                total_points += (score - 3000) / 1000
            
        # medic specific points:
        elif (await self.entity).role == IntRole.MEDIC:
            # life boosts: 3 points for every life boost

            total_points += self.life_boosts * 3

            # survival bonus: 2 points for being alive at the end of the game

            if self.lives_left > 0:
                total_points += 2

            # score bonus: 2 points (fractionally) for every 1000 points of score over 2000

            if score > 2000:
                total_points += ((score - 2000) / 1000) * 2

        return total_points

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
    player_states = fields.ManyToManyField("models.PlayerStates")
    scores = fields.ManyToManyField("models.Scores")
    entity_ends = fields.ManyToManyField("models.EntityEnds")
    laserball_stats = fields.ManyToManyField("models.LaserballStats")

    def __str__(self) -> str:
        return f"LaserballGame ({self.start_time})"
    
    def __repr__(self) -> str:
        return f"<LaserballGame ({self.tdf_name})>"
    
    async def get_red_score(self):
        return sum(map(lambda x: x[0], await self.entity_ends.filter(entity__team__color_name="Fire", entity__type="player").values_list("score")))
    
    async def get_blue_score(self):
        return sum(map(lambda x: x[0], await self.entity_ends.filter(entity__team__color_name="Ice", entity__type="player").values_list("score")))
    
    async def get_red_score_at_time(self, time):
        return sum(map(lambda x: x[0], await self.scores.filter(time__lte=time, entity__team__color_name="Fire").values_list("delta")))
    
    async def get_blue_score_at_time(self, time):
        return sum(map(lambda x: x[0], await self.scores.filter(time__lte=time, entity__team__color_name="Ice").values_list("delta")))
    
    async def get_rounds_at_time(self, time):
        return (await self.events.filter(time__lte=time, type=EventType.ROUND_END).count()) + 1

    async def get_possession_timeline(self) -> list[BallPossessionEvent]:
        """Returns a timeline of who had the ball at what time.

        The result is a list of possession markers (timestamp and owning entity) in game order. The last entry will
        always be a sentinel: The timestamp is the end of the game, and the entity is None.
        """
        events = await self.events.filter(type__in=
                         [EventType.GETS_BALL, EventType.CLEAR, EventType.MISSION_END, EventType.STEAL, EventType.PASS]
                         ).order_by("time").all()

        result = []

        for event in events:
            match event.type:
                case EventType.GETS_BALL:
                    result.append(BallPossessionEvent(timestamp_millis=event.time, entity_id=event.arguments[0]))
                case EventType.CLEAR:
                    result.append(BallPossessionEvent(timestamp_millis=event.time, entity_id=event.arguments[2]))
                case EventType.STEAL:
                    result.append(BallPossessionEvent(timestamp_millis=event.time, entity_id=event.arguments[0]))
                case EventType.PASS:
                    result.append(BallPossessionEvent(timestamp_millis=event.time, entity_id=event.arguments[2]))
                case EventType.MISSION_END:
                    result.append(BallPossessionEvent(timestamp_millis=event.time, entity_id=None))

        return result

    async def get_possession_times(self) -> dict[str, int]:
        """Returns the ball possession time for each entity.

        Entity ID is key, possession time in milliseconds in value.
        """
        possession_events = await self.get_possession_timeline()

        last_owner = None
        last_timestamp = 0

        possession_times = {}

        for event in possession_events:
            if last_owner and event.entity_id:
                possession_times[event.entity_id] = possession_times.get(event.entity_id, 0) + event.timestamp_millis - last_timestamp
            last_owner = event.entity_id
            last_timestamp = event.timestamp_millis

        return possession_times

    # funcs for getting win chance and draw chance

    async def get_win_chance_before_game(self) -> List[float]:
        """
        Returns the win chance before the game happened in the format [red, blue]
        """

        from helpers.ratinghelper import ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA

        # get the win chance for red team
        # this is based on the previous_elo of the player's entity_end

        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire", entity__type="player")

        # get the previous elo for each player

        previous_elos_red = []

        for entity_end in entity_ends_red:
            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                previous_elos_red.append(Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA))
            else:
                previous_elos_red.append(Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma))

        # get all the entity_ends for the green team

        entity_ends_blue = await self.entity_ends.filter(entity__team__color_name="Ice", entity__type="player")

        # get the previous elo for each player

        previous_elos_blue = []

        for entity_end in entity_ends_blue:
            if (await entity_end.entity).entity_id.startswith("@"):
                previous_elos_blue.append(Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA))
            else:
                previous_elos_blue.append(Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma))

        # get the win chance

        return model.predict_win([previous_elos_red, previous_elos_blue])
    

    async def get_win_chance_after_game(self) -> List[float]:
        """
        Returns the win chance **directly** after the game happened in the format [red, blue]
        """

        from helpers.ratinghelper import ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA

        # get the win chance for red team
        # this is based on the current_elo of the player's entity_end

        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire", entity__type="player")

        # get the current_elo for each player

        current_elos_red = []

        for entity_end in entity_ends_red:
            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                current_elos_red.append(Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA))
            else:
                current_elos_red.append(Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma))

        # get all the entity_ends for the green team

        entity_ends_blue = await self.entity_ends.filter(entity__team__color_name="Ice", entity__type="player")

        # get the current_elo for each player

        current_elos_blue = []

        for entity_end in entity_ends_blue:
            if (await entity_end.entity).entity_id.startswith("@"):
                current_elos_blue.append(Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA))
            else:
                current_elos_blue.append(Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma))

        # get the win chance

        return model.predict_win([current_elos_red, current_elos_blue])

    async def get_win_chance(self) -> List[float]:
        """
        Returns the win chance in the format [red, green]
        """
        from helpers.ratinghelper import ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA

        # get the win chance for red team
        # this is based on the previous_elo of the player's entity_end

        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire", entity__type="player")

        # get the previous elo for each player

        elos_red = []

        for entity_end in entity_ends_red:
            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                elos_red.append(Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA))
            else:
                player = await entity_end.get_player()
                elos_red.append(Rating(player.sm5_mu, player.sm5_sigma))

        # get all the entity_ends for the green team

        entity_ends_blue = await self.entity_ends.filter(entity__team__color_name="Ice", entity__type="player")

        # get the previous elo for each player

        elos_blue = []

        for entity_end in entity_ends_blue:
            if (await entity_end.entity).entity_id.startswith("@"):
                elos_blue.append(Rating(ASSUMED_SKILL_MU, ASSUMED_SKILL_SIGMA))
            else:
                player = await entity_end.get_player()
                elos_blue.append(Rating(player.sm5_mu, player.sm5_sigma))

        # get the win chance

        return model.predict_win([elos_red, elos_blue])
    
    def get_timestamp(self, time_zone: str="America/Los_Angeles") -> str:
        """
        Returns the timestamp of the game in the specified time zone
        """

        # get zero pad modifier for os
        if sys.platform == "win32":
            zero_pad = "#"
        else:
            zero_pad = "-"

        return strftime_ordinal(f"%A, %B {'{S}'} at %{zero_pad}I:%M %p", self.start_time)
    
    async def get_battlesuits(self) -> List[str]: # only the non-member players
        """
        Returns a list of entity_starts of battlesuits used in the game
        """

        return await self.entity_starts.filter(type="player", entity_id__startswith="@")
    
    async def get_players(self) -> List[str]: # all players
        """
        Returns a list of entity_starts of players in the game
        """

        return await self.entity_starts.filter(type="player")
    
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
    shots_fired = fields.IntField()
    shots_hit = fields.IntField()
    started_with_ball = fields.IntField()
    times_stolen = fields.IntField()
    times_blocked = fields.IntField()
    passes_received = fields.IntField()

    @property
    def mvp_points(self) -> float:
        mvp_points = 0

        mvp_points += self.goals   * 1
        mvp_points += self.assists * 0.75
        mvp_points += self.steals  * 0.5
        mvp_points += self.clears  * 0.25 # clear implies a steal so the total gained is 0.75
        mvp_points += self.blocks  * 0.3

        return mvp_points

    @property
    def score(self) -> int:
        """The score, as used in Laserforce player stats.

        The formula: Score = (Goals + Assists) * 10000 + Steals * 100 + Blocks
        See also: https://www.iplaylaserforce.com/games/laserball/.
        """
        return (self.goals + self.assists) * 10000 + self.steals * 100 + self.blocks

    async def to_dict(self):
        final = {}

        final["entity"] = (await self.entity).entity_id
        final["goals"] = self.goals
        final["assists"] = self.assists
        final["passes"] = self.passes
        final["steals"] = self.steals
        final["clears"] = self.clears
        final["blocks"] = self.blocks
        final["shots_fired"] = self.shots_fired
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