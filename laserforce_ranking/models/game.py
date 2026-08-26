from django.db import models
from abc import abstractmethod
import sys
from datetime import datetime
from models.types import Team, NAME_TO_TEAM, EntityType, IntRole, EventType, PlayerStateType, EntityEndType
from dataclasses import dataclass
import re

def suffix(date: int) -> str:
    return {1: "st", 2: "nd", 3: "rd"}.get(date % 20, "th")

def strftime_ordinal(format: str, time_: datetime) -> str:
    return time_.strftime(format).replace("{S}", str(time_.day) + suffix(time_.day))

class Team(models.Model):
    index = models.IntField()
    name = models.CharField(50)
    color_enum = models.IntField() # no idea what this enum is
    color_name = models.CharField(50)
    real_color_name = models.CharField(50) # this isn't in the tdf, but it's useful for the api (ex: "Fire" -> "Red")

    @property
    def enum(self) -> Team:
        return NAME_TO_TEAM[self.color_name]

    @property
    def short_name(self):
        """Returns the name without 'Team' in it to keep it short."""
        return re.sub(r"\s*Team\s*", "", self.name)
@dataclass
class PlayerInfo:
    """Information about a player in one particular game."""
    entity_start: EntityStarts
    entity_end: EntityEnds
    display_name: str

    @property
    def is_member(self) -> bool:
        return not self.entity_start.entity_id.startswith("@")

class EntityStart(models.Model):
    game = models.ForeignKey("Game", on_delete=models.CASCADE)
    time = models.IntegerField() # milliseconds since game start, measures when initalized
    entity_id = models.IntegerField()
    type = models.CharField(max_length=50, choices=EntityType)
    name = models.CharField(max_length=50) # name of the entity, usually a codename, battlesuit name, or target name
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    level = models.IntField() # LF level, 0 in games without levels
    role = models.IntegerField(choices=IntRole)
    battlesuit = models.CharField(max_length=50) # name of the battlesuit (only different if logged in)
    member_id = models.CharField(max_length=50, null=True) # member id of the player, if included in the tdf, otherwise null

    async def get_current_codename(self) -> str:
        # if the player has changed their name since the game, get the current name
        from models.player import Player
        player = await Player.objects.filter(entity_id=self.entity_id).afirst()
        if player:
            return player.codename
        return self.name

class Event(models.Model):
    game = models.ForeignKey("Game", on_delete=models.CASCADE)
    time = models.IntegerField()  # time in milliseconds
    type = models.CharField(choices=EventType)
    # The first entity involved in the action, typically the one performing the action.
    # Can be empty in some cases, for example global events such as "* Mission Start *".
    entity1 = models.CharField(50, default="")

    # The action being performed by the entity (or the global event, such as "* Mission Start *").
    action = models.CharField(50, default="")

    # The second entity involved in the action, typically the entity that something is being done to.
    # This can be empty if the action doesn't involve a specific recipient, for example if the main entity
    # activates a nuke.
    entity2 = models.CharField(50, default="")

# player status updates
class PlayerState(models.Model):
    game = models.ForeignKey("Game", on_delete=models.CASCADE)
    time = models.IntegerField() # time in milliseconds
    entity = models.ForeignKey("EntityStart", on_delete=models.CASCADE)
    state = models.IntegerField(choices=PlayerStateType)

# delta score updates
class Score(models.Model):
    game = models.ForeignKey("Game", on_delete=models.CASCADE)
    time = models.IntegerField() # time in milliseconds
    entity = models.ForeignKey("EntityStart", on_delete=models.CASCADE)
    old = models.IntegerField() # old score
    delta = models.IntegerField() # change in score
    new = models.IntegerField() # new score

class EntityEnd(models.Model):
    game = models.ForeignKey("Game", on_delete=models.CASCADE)
    time = models.IntegerField() # milliseconds since game start, measures when destroyed or left
    entity = models.ForeignKey("EntityStart", on_delete=models.CASCADE)
    type = models.CharField(max_length=50, choices=EntityEndType)

    # TODO: current and previous ratings globally and arena-specific

@dataclass
class PlayerInfo:
    """Information about a player in one particular game."""
    entity_start: EntityStart
    entity_end: EntityEnd
    display_name: str

    @property
    def is_member(self) -> bool:
        return not self.entity_start.entity_id.startswith("@")


# base game type for a laserforce game imported from tdf
class Game(models.Model):
    id = models.AutoField(primary_key=True)
    site_id = models.CharField(max_length=50)
    tdf_name = models.CharField(max_length=100) # name of tdf in filesystem for storage
    file_version = models.DecimalField() # version is a decimal number, we can just store it as a string
    software_version = models.CharField(max_length=20)  # ^
    arena = models.CharField(max_length=20) # continent-arena, (ex: 4-43)
    mission_type = models.IntegerField() # mission type, depends on site
    mission_name = models.CharField(max_length=100)
    ranked = models.BooleanField() # will this game affect player ratings and stats.
    ended_early = models.BooleanField() # did the game end early?
    # Real-life time when the game started. Keep in mind that MySQL does not store timezone information, so this is
    # a DATETIME(6) field. It has microsecond precision but no concept of timezone, so when you read it as a datetime
    # object, it will be the local time at the location where it was played, but timezone set to UTC.
    # Likewise, when you initialize this value with a datetime object, set the timezone to UTC and the time to whatever
    # it was at the local site to prevent headaches.
    start_time = models.DateTimeField()
    mission_duration = models.IntegerField() # how long the game can last if it doesn't end early, in milliseconds
    log_time = models.DateTimeField(auto_now_add=True)
    # TODO: related fields

    @property
    @abstractmethod
    def short_type(self) -> str:
        """
        Returns the short type of the game.
        This is used for the API and should be a short string that describes the game type.
        For example, "laserball" or "sm5".
        """
        raise NotImplementedError("Subclasses must implement short_type property")

    def get_timestamp(self, time_zone: str = "America/Los_Angeles") -> str:
        """
        Returns the timestamp of the game in the specified time zone
        """

        # get zero pad modifier for os
        if sys.platform == "win32":
            zero_pad = "#"
        else:
            zero_pad = "-"

        return strftime_ordinal(f"%A, %B {'{S}'}, %Y at %{zero_pad}I:%M %p", self.start_time)
    
    class Meta:
        abstract = True