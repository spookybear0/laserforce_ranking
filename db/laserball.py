try:
    from openskill.models import PlackettLuceRating as Rating
except ImportError:
    from openskill.models.weng_lin.plackett_luce import PlackettLuceRating as Rating
from db.types import Team, EventType, BallPossessionEvent, ElementTeam
from helpers.datehelper import strftime_ordinal
from tortoise import Model, fields
from typing import List
import sys

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
    
    async def get_team_score(self, team: ElementTeam) -> int:
        return sum(map(lambda x: x[0], await self.entity_ends.filter(entity__team__color_name=team.value, entity__type="player").values_list("score")))

    async def get_team_score_at_time(self, team: ElementTeam, time: int) -> int:
        return sum(map(lambda x: x[0], await self.scores.filter(time__lte=time, entity__team__color_name=team.value).values_list("delta")))
    
    async def get_rounds_at_time(self, time) -> int:
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

        from helpers.ratinghelper import MU, SIGMA

        # get the win chance for red team
        # this is based on the previous_elo of the player's entity_end

        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire", entity__type="player")

        # get the previous elo for each player

        previous_elos_red = []

        for entity_end in entity_ends_red:
            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                previous_elos_red.append(Rating(MU, SIGMA))
            else:
                previous_elos_red.append(Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma))

        # get all the entity_ends for the green team

        entity_ends_blue = await self.entity_ends.filter(entity__team__color_name="Ice", entity__type="player")

        # get the previous elo for each player

        previous_elos_blue = []

        for entity_end in entity_ends_blue:
            if (await entity_end.entity).entity_id.startswith("@"):
                previous_elos_blue.append(Rating(MU, SIGMA))
            else:
                previous_elos_blue.append(Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma))

        # get the win chance

        from helpers.ratinghelper import model
        return model.predict_win([previous_elos_red, previous_elos_blue])
    

    async def get_win_chance_after_game(self) -> List[float]:
        """
        Returns the win chance **directly** after the game happened in the format [red, blue]
        """

        from helpers.ratinghelper import MU, SIGMA

        # get the win chance for red team
        # this is based on the current_elo of the player's entity_end

        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire", entity__type="player")

        # get the current_elo for each player

        current_elos_red = []

        for entity_end in entity_ends_red:
            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                current_elos_red.append(Rating(MU, SIGMA))
            else:
                current_elos_red.append(Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma))

        # get all the entity_ends for the green team

        entity_ends_blue = await self.entity_ends.filter(entity__team__color_name="Ice", entity__type="player")

        # get the current_elo for each player

        current_elos_blue = []

        for entity_end in entity_ends_blue:
            if (await entity_end.entity).entity_id.startswith("@"):
                current_elos_blue.append(Rating(MU, SIGMA))
            else:
                current_elos_blue.append(Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma))

        # get the win chance

        from helpers.ratinghelper import model
        return model.predict_win([current_elos_red, current_elos_blue])

    async def get_win_chance(self) -> List[float]:
        """
        Returns the win chance in the format [red, green]
        """
        from helpers.ratinghelper import MU, SIGMA

        # get the win chance for red team
        # this is based on the previous_elo of the player's entity_end

        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire", entity__type="player")

        # get the previous elo for each player

        elos_red = []

        for entity_end in entity_ends_red:
            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                elos_red.append(Rating(MU, SIGMA))
            else:
                player = await entity_end.get_player()
                elos_red.append(Rating(player.sm5_mu, player.sm5_sigma))

        # get all the entity_ends for the green team

        entity_ends_blue = await self.entity_ends.filter(entity__team__color_name="Ice", entity__type="player")

        # get the previous elo for each player

        elos_blue = []

        for entity_end in entity_ends_blue:
            if (await entity_end.entity).entity_id.startswith("@"):
                elos_blue.append(Rating(MU, SIGMA))
            else:
                player = await entity_end.get_player()
                elos_blue.append(Rating(player.sm5_mu, player.sm5_sigma))

        # get the win chance

        from helpers.ratinghelper import model
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
    
    async def to_dict(self) -> dict:
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

        return final