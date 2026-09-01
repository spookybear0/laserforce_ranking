from django.db import models
from abc import abstractmethod
import sys
from datetime import datetime
from .types import TeamType, NAME_TO_TEAM, EntityType, IntRole, EventType, PlayerStateType, EntityEndType
from dataclasses import dataclass
import re
from django_enum import EnumField
from django.urls import reverse

def suffix(date: int) -> str:
    return {1: "st", 2: "nd", 3: "rd"}.get(date % 20, "th")

def strftime_ordinal(format: str, time_: datetime) -> str:
    return time_.strftime(format).replace("{S}", str(time_.day) + suffix(time_.day))

class Team(models.Model):
    game = models.ForeignKey("Game", on_delete=models.CASCADE, related_name="teams")
    index = models.PositiveSmallIntegerField()
    name = models.CharField(50)
    color_enum = models.PositiveSmallIntegerField() # no idea what this enum is
    color_name = models.CharField(50)

    real_color_name = models.CharField(50) # this isn't in the tdf, but it's useful for the api (ex: "Fire" -> "Red")
    score = models.IntegerField() # total score for the team, useful for getting fast info

    entity_starts = models.ManyToManyField("EntityStart", related_name="teams")

    @property
    def enum(self) -> TeamType:
        return NAME_TO_TEAM[self.color_name]

    @property
    def short_name(self):
        """Returns the name without 'Team' in it to keep it short."""
        return re.sub(r"\s*Team\s*", "", self.name)
    
    def __str__(self):
        return f"{self.name} (Game {self.game.id})"

class EntityStart(models.Model):
    game = models.ForeignKey("Game", on_delete=models.CASCADE, related_name="entity_starts")
    time = models.IntegerField() # milliseconds since game start, measures when initalized
    entity_id = models.CharField(max_length=50) # ex: #ZRbsz (member) or @71 (battlesuit/base)
    type = EnumField(EntityType)
    name = models.CharField(max_length=50) # name of the entity, usually a codename, battlesuit name, or target name
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    level = models.SmallIntegerField() # LF level, 0 in games without levels
    role = EnumField(IntRole) # role of the player, if applicable, otherwise 0
    battlesuit = models.CharField(max_length=50, null=True) # name of the battlesuit (only different if logged in)
    member_id = models.CharField(max_length=50, null=True) # member id of the player, if included in the tdf, otherwise null
    entity_end = models.OneToOneField("EntityEnd", on_delete=models.SET_NULL, null=True, blank=True) # the entity end for this entity, if it exists

    async def get_current_codename(self) -> str:
        # if the player has changed their name since the game, get the current name
        from models.player import Player
        player = await Player.objects.filter(entity_id=self.entity_id).afirst()
        if player:
            return player.codename
        return self.name
    
    async def get_penalty_count(self) -> int:
        """Returns the number of penalties this player received in this game."""
        penalty_count = await self.game.events.filter(
            type=EventType.PENALTY,
            entity1=self.entity_id
        ).acount()
        return penalty_count
    
    def __str__(self):
        return f"{self.name} ({self.entity_id}) - {self.type.name} - Game {self.game.id}"

class Event(models.Model):
    game = models.ForeignKey("Game", on_delete=models.CASCADE, related_name="events")
    time = models.IntegerField()  # time in milliseconds
    type = EnumField(EventType)
    # The first entity involved in the action, typically the one performing the action.
    # Can be empty in some cases, for example global events such as "* Mission Start *".
    entity1 = models.CharField(50, default="")

    # The action being performed by the entity (or the global event, such as "* Mission Start *").
    action = models.CharField(50, default="")

    # The second entity involved in the action, typically the entity that something is being done to.
    # This can be empty if the action doesn't involve a specific recipient, for example if the main entity
    # activates a nuke.
    entity2 = models.CharField(50, default="")

    def __str__(self):
        return f"{self.type.name}: {self.entity1} {self.action} {self.entity2} - Game {self.game.id}"
    
    class Meta:
        ordering = ["time"] # order events by time

# player status updates
class PlayerState(models.Model):
    game = models.ForeignKey("Game", on_delete=models.CASCADE, related_name="player_states")
    time = models.IntegerField() # time in milliseconds
    entity = models.ForeignKey("EntityStart", on_delete=models.CASCADE)
    state = EnumField(PlayerStateType) # state of the player

    def __str__(self):
        return f"{self.state.name} - {self.entity.name} - Game {self.game.id}"

# delta score updates
class Score(models.Model):
    game = models.ForeignKey("Game", on_delete=models.CASCADE, related_name="scores")
    time = models.IntegerField() # time in milliseconds
    entity = models.ForeignKey("EntityStart", on_delete=models.CASCADE)
    old = models.IntegerField() # old score
    delta = models.SmallIntegerField() # change in score
    new = models.IntegerField() # new score

    def __str__(self):
        return f"{self.entity.name} - {self.old} -> {self.new} (delta: {self.delta}) - Game {self.game.id}"

class EntityEnd(models.Model):
    game = models.ForeignKey("Game", on_delete=models.CASCADE, related_name="entity_ends")
    time = models.IntegerField() # milliseconds since game start, measures when destroyed or left
    entity = models.ForeignKey("EntityStart", on_delete=models.CASCADE)
    type = EnumField(EntityEndType) # how the entity ended
    score = models.IntegerField() # final score for the entity

    """
    ratings = {
        "previous": {
            "global": {
                "mu": float,
                "sigma": float,
            },
            "global_role": {
                "mu": float,
                "sigma": float,
            },
            "site": {
                "mu": float,
                "sigma": float,
            },
            "site_role": {
                "mu": float,
                "sigma": float,
            },
        },
        "current": {
            "global": {
                "mu": float,
                "sigma": float,
            },
            "global_role": {
                "mu": float,
                "sigma": float,
            },
            "site": {
                "mu": float,
                "sigma": float,
            },
            "site_role": {
                "mu": float,
                "sigma": float,
            },
        }
    }
    """
    ratings = models.JSONField(null=True) # current and previous ratings, if available
    video = models.URLField(null=True) # video of the game from this player's perspective, if available

    def __str__(self):
        return f"{self.entity.name} - {self.type.name} - Game {self.game.id}"

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
    site_id = models.SlugField() # continent-arena (ex: 4-43)
    tdf_name = models.CharField(max_length=100) # name of tdf in filesystem for storage
    file_version = models.CharField(max_length=20) # version is a decimal number, we can just store it as a string
    software_version = models.CharField(max_length=20)  # ^
    mission_type = models.PositiveSmallIntegerField() # mission type, depends on site
    mission_name = models.CharField(max_length=100)
    ranked = models.BooleanField() # will this game affect player ratings and stats.
    force_ended_early = models.BooleanField() # did someone stop this game with the end game button
    # Real-life time when the game started. With timezone of the local arena.
    start_time = models.DateTimeField()
    mission_duration = models.DurationField() # how long the game can last if it doesn't end early
    duration = models.DurationField() # how long the game actually lasted, can be less than mission_duration if it ended early
    penalty_amount = models.SmallIntegerField() # how much score is added for each penalty, can be negative (ex: 0, -1000)

    # FORIEGN KEYS AND RELATED NAMES
    # teams is a related name for the Team model, which has a foreign key to this model
    # entity_starts is a related name for the EntityStart model, which has a foreign key to this model
    # events is a related name for the Event model, which has a foreign key to this model
    # player_states is a related name for the PlayerState model, which has a foreign key to this model
    # scores is a related name for the Score model, which has a foreign key to this model
    # entity_ends is a related name for the EntityEnd model, which has a foreign key to this model
    
    video = models.URLField(null=True) # video of the game (usually just scoreboard), if available

    winner = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name="won_games")

    team1_size = models.PositiveSmallIntegerField(null=True) # quick and dirty way to get team sizes
    team2_size = models.PositiveSmallIntegerField(null=True) # quick and dirty way to get team sizes

    log_time = models.DateTimeField(auto_now_add=True)

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
    
    def get_absolute_url(self):
        return reverse("game_detail", kwargs={"tdf_name": self.tdf_name})

    def __str__(self):
        return f"Game {self.id} - {self.mission_name} at {self.site_id} on {self.start_time}"