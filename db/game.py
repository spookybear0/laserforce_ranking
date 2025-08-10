# flake8: noqa: F821
# Disable "unknown name" because we're using forward references here that flake8 has no love for.

from __future__ import annotations

import re
from dataclasses import dataclass

from tortoise import Model, fields
from helpers.cachehelper import cache
from db.types import Team, IntRole, EventType, PlayerStateType, NAME_TO_TEAM
from typing import List, Optional
from abc import ABC, abstractmethod
from helpers.datehelper import strftime_ordinal
import sys
try:
    from openskill.models import PlackettLuceRating as Rating
except ImportError:
    from openskill.models.weng_lin.plackett_luce import PlackettLuceRating as Rating


# general game stuff

class Teams(Model):
    index = fields.IntField()
    name = fields.CharField(50)
    color_enum = fields.IntField()  # no idea what this enum is
    color_name = fields.CharField(50)
    real_color_name = fields.CharField(50)  # this isn't in the tdf, but it's useful for the api (ex: "Fire" -> "Red")

    @property
    def enum(self) -> Team:
        return NAME_TO_TEAM[self.color_name]

    @property
    def short_name(self):
        """Returns the name without 'Team' in it to keep it short."""
        return re.sub(r"\s*Team\s*", "", self.name)

    async def to_dict(self) -> dict:
        final = {}

        final["index"] = self.index
        final["name"] = self.name
        final["color_enum"] = int(self.color_enum)
        final["color_name"] = self.color_name
        final["real_color_name"] = self.real_color_name

        return final
    
    def __str__(self) -> str:
        return f"<Team index={self.index} name={self.name} color_enum={self.color_enum} color_name={self.color_name} real_color_name={self.real_color_name}>"
    
    def __repr__(self) -> str:
        return str(self)


class EntityStarts(Model):
    id = fields.IntField(pk=True)
    time = fields.IntField()  # time in milliseconds
    entity_id = fields.CharField(50)  # id of the entity
    type = fields.CharField(50)  # can be [player, standard-target, maybe more]
    name = fields.CharField(75)  # name of the entity
    team = fields.ForeignKeyField("models.Teams")
    level = fields.IntField()  # for sm5 this is always 0
    role = fields.IntEnumField(IntRole)  # 0 for targets, no idea what it is for laserball
    battlesuit = fields.CharField(50)  # for targets its the target name
    member_id = fields.CharField(50, null=True)  # only for newer games (or ones with the option to include member_id)

    async def get_player(self) -> "Player":
        # get the player object from the entity
        from db.player import Player
        return await Player.filter(entity_id=self.entity_id).first()

    async def get_entity_end(self) -> "EntityEnds":
        return await EntityEnds.filter(entity__id=self.id).first()

    async def get_sm5_stats(self) -> "SM5Stats":
        from db.sm5 import SM5Stats
        return await SM5Stats.filter(entity__id=self.id).first()

    async def get_score(self) -> int:
        return (await self.get_entity_end()).score

    async def to_dict(self) -> dict:
        final = {}

        final["id"] = self.id
        final["time"] = self.time
        final["entity_id"] = self.entity_id
        final["type"] = self.type
        final["name"] = self.name
        final["team"] = (await self.team).real_color_name
        final["team_index"] = (await self.team).index
        final["level"] = self.level
        final["role"] = int(self.role)
        final["battlesuit"] = self.battlesuit
        final["member_id"] = self.member_id

        return final

    def __str__(self) -> str:
        return f"<EntityStarts id={self.id} entity_id={self.entity_id} type={self.type} name={self.name} team={self.team} level={self.level} role={self.role} battlesuit={self.battlesuit} member_id={self.member_id}>"

    def __repr__(self) -> str:
        return str(self)


class Events(Model):
    time = fields.IntField()  # time in milliseconds
    type = fields.CharEnumField(EventType)
    # variable number of fields depending on type of event
    # can be token or string for announcement
    # now make the field
    # Note that it's typically easier to just use entity1, action, and entity2 instead of arguments.
    # This field will remain for legacy reasons.
    arguments = fields.JSONField()  # list of arguments

    # The first entity involved in the action, typically the one performing the action.
    # Can be empty in some cases, for example global events such as "* Mission Start *".
    entity1 = fields.CharField(50, default="")

    # The action being performed by the entity (or the global event, such as "* Mission Start *").
    action = fields.CharField(50, default="")

    # The second entity involved in the action, typically the entity that something is being done to.
    # This can be empty if the action doesn't involve a specific recipient, for example if the main entity
    # activates a nuke.
    entity2 = fields.CharField(50, default="")

    async def to_dict(self) -> dict:
        final = {}

        final["time"] = self.time
        final["type"] = self.type.value
        final["arguments"] = self.arguments

        return final
    
    def __str__(self) -> str:
        return f"<Event time={self.time} type={self.type} arguments={self.arguments}>"
    
    def __repr__(self) -> str:
        return str(self)


class PlayerStates(Model):
    time = fields.IntField()  # time in milliseconds
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="id")
    state = fields.IntEnumField(PlayerStateType)

    async def to_dict(self) -> dict:
        final = {}

        final["time"] = self.time
        final["entity"] = (await self.entity).entity_id
        final["state"] = self.state

        return final


class Scores(Model):
    time = fields.IntField()  # time in milliseconds
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="id")
    old = fields.IntField()  # old score
    delta = fields.IntField()  # change in score
    new = fields.IntField()  # new score

    async def to_dict(self) -> dict:
        final = {}

        final["time"] = self.time
        final["entity"] = (await self.entity).entity_id
        final["old"] = self.old
        final["delta"] = self.delta
        final["new"] = self.new

        return final

    def __str__(self) -> str:
        return f"<Score {self.old} -> {self.new} delta=({self.delta})>"

    def __repr__(self) -> str:
        return str(self)


class EntityEnds(Model):
    time = fields.IntField()  # time in milliseconds
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="id")
    type = fields.IntField()  # don't know what enum this is
    score = fields.IntField()
    current_rating_mu = fields.FloatField(null=True)  # only for players, only for ranked games
    current_rating_sigma = fields.FloatField(null=True)  # only for players, only for ranked games
    previous_rating_mu = fields.FloatField(null=True)  # only for players, only for ranked games
    previous_rating_sigma = fields.FloatField(null=True)  # only for players, only for ranked games

    @property
    def current_rating(self) -> Optional[float]:
        """Returns the current rating (mu - 3 * sigma) after the game ended."""
        if self.current_rating_mu is None or self.current_rating_sigma is None:
            return None
        return self.current_rating_mu - 3 * self.current_rating_sigma
    
    @property
    def previous_rating(self) -> Optional[float]:
        """Returns the previous rating (mu - 3 * sigma) before the game ended."""
        if self.previous_rating_mu is None or self.previous_rating_sigma is None:
            return None
        return self.previous_rating_mu - 3 * self.previous_rating_sigma

    @property
    def rating_difference(self) -> Optional[float]:
        """Returns the rating (mu - 3 * sigma) difference after the game ended."""
        if self.current_rating is None or self.previous_rating is None:
            return None
        
        return self.current_rating - self.previous_rating
    
    @property
    def rating_difference_mu(self) -> Optional[float]:
        """Returns the rating mu difference after the game ended."""
        if self.current_rating_mu is None or self.previous_rating_mu is None:
            return None
        
        return self.current_rating_mu - self.previous_rating_mu
    
    @property
    def rating_difference_sigma(self) -> Optional[float]:
        """Returns the rating sigma difference after the game ended."""
        if self.current_rating_sigma is None or self.previous_rating_sigma is None:
            return None
        
        return self.current_rating_sigma - self.previous_rating_sigma

    async def get_player(self) -> "Player":
        # get the player object from the entity
        from db.player import Player
        return await Player.filter(entity_id=(await self.entity).entity_id).first()

    async def get_entity_start(self) -> EntityStarts:
        return await self.entity

    async def get_sm5_stats(self) -> "SM5Stats":
        from db.sm5 import SM5Stats
        return await SM5Stats.filter(entity__id=(await self.entity).entity_id).first()

    async def to_dict(self) -> dict:
        final = {}

        final["time"] = self.time
        final["entity"] = (await self.entity).entity_id
        final["type"] = self.type
        final["score"] = self.score
        final["current_rating_mu"] = self.current_rating_mu
        final["current_rating_sigma"] = self.current_rating_sigma
        if self.current_rating_mu and self.current_rating_sigma:
            final["current_rating"] = self.current_rating_mu - 3 * self.current_rating_sigma
        else:
            final["current_rating"] = None
        final["previous_rating_mu"] = self.previous_rating_mu
        final["previous_rating_sigma"] = self.previous_rating_sigma
        if self.previous_rating_mu and self.previous_rating_sigma:
            final["previous_rating"] = self.previous_rating_mu - 3 * self.previous_rating_sigma
        else:
            final["previous_rating"] = None

        return final

    def __str__(self) -> str:
        return f"<EntityEnd score={self.score} type={self.type} time={self.time}>"

    def __repr__(self) -> str:
        return str(self)


@dataclass
class PlayerInfo:
    """Information about a player in one particular game."""
    entity_start: EntityStarts
    entity_end: EntityEnds
    display_name: str

    @property
    def is_member(self) -> bool:
        return not self.entity_start.entity_id.startswith("@")

# abstract class for game

class Game(Model):
    id = fields.IntField(pk=True)
    winner = fields.CharEnumField(Team)
    winner_color = fields.CharField(20)
    tdf_name = fields.CharField(100)
    file_version = fields.CharField(20)  # version is a decimal number, we can just store it as a string
    software_version = fields.CharField(20)  # ditto ^
    arena = fields.CharField(20)  # x-y, x=continent, y=arena (ex: 4-43)
    mission_type = fields.IntField()  # no idea what this enum is
    mission_name = fields.CharField(100)
    ranked = fields.BooleanField()  # will this game affect player ratings and stats.
    ended_early = fields.BooleanField()  # did the game end early?
    # Real-life time when the game started. Keep in mind that MySQL does not store timezone information, so this is
    # a DATETIME(6) field. It has microsecond precision but no concept of timezone, so when you read it as a datetime
    # object, it will be the local time at the location where it was played, but timezone set to UTC.
    # Likewise, when you initialize this value with a datetime object, set the timezone to UTC and the time to whatever
    # it was at the local site to prevent headaches.
    start_time = fields.DatetimeField()
    mission_duration = fields.IntField()  # in seconds
    log_time = fields.DatetimeField(auto_now_add=True)
    # Field that is not currently stored: penalty (the amount of points deducted from when a player gets a penalty ex: 0, -1000)
    teams = fields.ManyToManyField("models.Teams")
    entity_starts = fields.ManyToManyField("models.EntityStarts")
    events = fields.ManyToManyField("models.Events")
    player_states = fields.ManyToManyField("models.PlayerStates")
    scores = fields.ManyToManyField("models.Scores")
    entity_ends = fields.ManyToManyField("models.EntityEnds")

    @property
    @abstractmethod
    def short_type(self) -> str:
        """
        Returns the short type of the game.
        This is used for the API and should be a short string that describes the game type.
        For example, "laserball" or "sm5".
        """
        raise NotImplementedError("Subclasses must implement short_type property")

    # win chance related functions

    @cache()
    async def get_win_chance(self, timeframe: Optional[str] = None) -> List[float]:
        """
        Calculates the win chance for the game based on the players' ratings.
        The timeframe can be "before", "after", or None.

        "before" will use the previous ratings of the players and show the prediciton based on data only up to the start of the game.
        "after" will use ratings recorded directly after the game ended, so it will include the game itself in the prediction.
        None will use the current ratings of the players, so it will include all games played by the players up to now.

        Returns the win chance in the format [team1, team2] / [red, green] / [red, blue]
        """
        from helpers.ratinghelper import MU, SIGMA


        async def get_rating(entity_end: EntityEnds) -> Rating:
            """
            Returns the player's rating.
            If the player is not a member, returns a default rating.
            """
            
            # get laserball/sm5 rating before/after

            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                return Rating(MU, SIGMA)
            else:
                player = await entity_end.get_player()
                if timeframe == "before":
                    return Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma)
                elif timeframe == "after":
                    return Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma)
                else:
                    return Rating(
                        getattr(player, f"{self.short_type}_mu", MU),
                        getattr(player, f"{self.short_type}_sigma", SIGMA)
                    )
            

        teams = await self.get_teams()

        # get the win chance for red team
        # this is based on the previous_elo of the player's entity_end

        # get all the entity_ends for the red team

        entity_ends_team1 = await self.entity_ends.filter(entity__team__color_name=teams[0].color_name, entity__type="player")

        # get the previous elo for each player

        elos_team1 = [await get_rating(entity_end) for entity_end in entity_ends_team1]

        # get all the entity_ends for the green team

        entity_ends_team2 = await self.entity_ends.filter(entity__team__color_name=teams[1].color_name, entity__type="player")

        # get the previous elo for each player

        elos_team2 = [await get_rating(entity_end) for entity_end in entity_ends_team2]

        # get the win chance

        from helpers.ratinghelper import model
        return model.predict_win([
            elos_team1,
            elos_team2
        ])
    
    async def get_win_chance_before_game(self) -> List[float]:
        """
        Returns the win chance before the game started.
        This is based on the previous ratings of the players.
        """
        return await self.get_win_chance("before")
    
    async def get_win_chance_after_game(self) -> List[float]:
        """
        Returns the win chance after the game ended.
        This is based on the ratings of the players after the game ended.
        """
        return await self.get_win_chance("after")
    
    def get_timestamp(self, time_zone: str = "America/Los_Angeles") -> str:
        """
        Returns the timestamp of the game in the specified time zone
        """

        # get zero pad modifier for os
        if sys.platform == "win32":
            zero_pad = "#"
        else:
            zero_pad = "-"

        return strftime_ordinal(f"%A, %B {'{S}'} at %{zero_pad}I:%M %p", self.start_time)
    
    async def get_battlesuits(self) -> List[str]:  # only the non-member players
        """
        Returns a list of entity_starts of battlesuits used in the game
        """

        return await self.entity_starts.filter(type="player", entity_id__startswith="@")

    async def get_players(self) -> List[str]:  # all players
        """
        Returns a list of entity_starts of players in the game
        """

        return await self.entity_starts.filter(type="player")
    
    async def get_teams(self) -> List[Team]:
        """
        Returns a list of teams in the game excluding neutral teams
        """

        return await self.teams.filter(name__not_in=["Neutral", "None"])
    
    # game id

    async def get_previous_game_id(self) -> Optional[int]:
        """
        Returns the game id of the previous game
        """

        id_ = await self.__class__.filter(start_time__lt=self.start_time).order_by("-start_time").values_list("id", flat=True)
        if not id_:
            return None
        return id_[0]

    async def get_next_game_id(self) -> Optional[int]:
        """
        Returns the game id of the next game
        """

        id_ = await self.__class__.filter(start_time__gt=self.start_time).order_by("start_time").values_list("id", flat=True)
        if not id_:
            return None
        return id_[0]

    async def to_dict(self, full: bool = True, player_stats=None) -> dict:
        # convert the entire game to a dict
        # this is used for the api

        await self.fetch_related("teams", "entity_starts", "events", "player_states", "scores", "entity_ends")

        final = {}

        final["id"] = self.id
        final["short_type"] = self.short_type
        final["winner"] = self.winner.value
        final["winner_color"] = self.winner_color
        final["tdf_name"] = self.tdf_name
        final["file_version"] = self.file_version
        final["software_version"] = self.software_version
        final["arena"] = self.arena
        final["mission_type"] = self.mission_type
        final["mission_name"] = self.mission_name
        final["ranked"] = self.ranked
        final["ended_early"] = self.ended_early
        final["start_time"] = self.start_time.timestamp()
        final["mission_duration"] = self.mission_duration
        final["log_time"] = self.log_time.timestamp()

        if full:
            final["teams"] = [await team.to_dict() for team in self.teams]
            final["events"] = [await event.to_dict() for event in self.events]
            final["player_states"] = [await player_state.to_dict() for player_state in self.player_states]
            final["scores"] = [await score.to_dict() for score in self.scores]
        final["entity_starts"] = [await entity_start.to_dict() for entity_start in self.entity_starts]
        final["entity_ends"] = [await entity_end.to_dict() for entity_end in self.entity_ends]

        if player_stats is not None:
            final["player_entity_start"] = await (
                await self.get_entity_start_from_name(player_stats.codename)).to_dict()
            try:
                final["player_entity_end"] = await (await self.get_entity_end_from_name(player_stats.codename)).to_dict()
            except AttributeError:
                final["player_entity_end"] = None # no idea why this is needed

        return final
    
    class Meta:
        abstract = True