try:
    from openskill.models import PlackettLuceRating as Rating
except ImportError:
    from openskill.models.weng_lin.plackett_luce import PlackettLuceRating as Rating
import sys
from typing import List, Optional

from tortoise import Model, fields

from db.game import EntityStarts, EntityEnds
from db.types import Team, EventType, BallPossessionEvent
from helpers.cachehelper import cache
from db.game import Game
from abc import abstractmethod

class LaserballGame(Game):
    # many to many relationships (define reverse relationship)
    teams = fields.ManyToManyField("models.Teams", related_name="laserballgames")
    entity_starts = fields.ManyToManyField("models.EntityStarts", related_name="laserballgames")
    events = fields.ManyToManyField("models.Events", related_name="laserballgames")
    player_states = fields.ManyToManyField("models.PlayerStates", related_name="laserballgames")
    scores = fields.ManyToManyField("models.Scores", related_name="laserballgames")
    entity_ends = fields.ManyToManyField("models.EntityEnds", related_name="laserballgames")
    # my own stats tracker for laserball (not included in tdf)
    laserball_stats = fields.ManyToManyField("models.LaserballStats")

    def __str__(self) -> str:
        return f"LaserballGame(id={self.id}, start_time={self.start_time}, arena={self.arena}, mission_type={self.mission_type}, " \
                f"mission_name={self.mission_name}, winner={self.winner}, ranked={self.ranked})"
    
    def __repr__(self) -> str:
        return str(self)
    
    @property
    @abstractmethod
    def short_type(self) -> str:
        return "laserball"

    async def get_entity_start_from_name(self, name: str) -> Optional[EntityStarts]:
        return await self.entity_starts.filter(name=name).first()

    async def get_entity_end_from_name(self, name: str) -> Optional[EntityEnds]:
        return await self.entity_ends.filter(entity__name=name).first()

    async def get_laserball_stat_from_name(self, name: str) -> Optional["LaserballStats"]:
        return await self.laserball_stats.filter(entity__name=name).first()

    async def get_team_score(self, team: Team) -> int:
        # TODO: optimize
        return sum(map(lambda x: x[0], await self.entity_ends.filter(entity__team__color_name=team.element,
                                                                     entity__type="player").values_list("score")))

    async def get_team_score_at_time(self, team: Team, time: int) -> int:
        # TODO: optimize
        return sum(map(lambda x: x[0],
                       await self.scores.filter(time__lte=time, entity__team__color_name=team.element).values_list(
                           "delta")))

    async def get_rounds_at_time(self, time) -> int:
        return (await self.events.filter(time__lte=time, type=EventType.ROUND_END).count()) + 1

    @cache()
    async def get_possession_timeline(self) -> list[BallPossessionEvent]:
        """Returns a timeline of who had the ball at what time.

        The result is a list of possession markers (timestamp and owning entity) in game order. The last entry will
        always be a sentinel: The timestamp is the end of the game, and the entity is None.
        """
        events = await self.events.filter(type__in=
                                          [EventType.GETS_BALL, EventType.CLEAR, EventType.MISSION_END, EventType.STEAL,
                                           EventType.PASS]
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
                possession_times[event.entity_id] = possession_times.get(event.entity_id,
                                                                         0) + event.timestamp_millis - last_timestamp
            last_owner = event.entity_id
            last_timestamp = event.timestamp_millis

        return possession_times

    @cache()
    async def to_dict(self, full: bool = True, player_stats=None) -> dict:
        # convert the entire game to a dict
        # this is used for the api
        final = await Game.to_dict(self, full=full, player_stats=player_stats)

        final["laserball_stats"] = [await (await laserball_stats).to_dict() for laserball_stats in
                                    await self.laserball_stats.all()]

        if player_stats is not None:
            final["player_laserball_stats"] = await (
                await self.get_laserball_stat_from_name(player_stats.codename)
            ).to_dict()

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

        mvp_points += self.goals * 1
        mvp_points += self.assists * 0.75
        mvp_points += self.steals * 0.5
        mvp_points += self.clears * 0.25  # clear implies a steal so the total gained is 0.75
        mvp_points += self.blocks * 0.3

        return mvp_points

    @property
    def score(self) -> int:
        """The score, as used in Laserforce player stats.

        The formula: Score = (Goals + Assists) * 10000 + Steals * 100 + Blocks
        See also: https://www.iplaylaserforce.com/games/laserball/.
        """
        return (self.goals + self.assists) * 10000 + self.steals * 100 + self.blocks

    async def to_dict(self) -> dict:
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
        final["mvp_points"] = self.mvp_points
        final["score"] = self.score

        return final
