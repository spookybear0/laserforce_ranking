# flake8: noqa: F821
# Disable "unknown name" because we're using forward references here that flake8 has no love for.

from __future__ import annotations

try:
    from openskill.models import PlackettLuceRating as Rating
except ImportError:
    from openskill.models.weng_lin.plackett_luce import PlackettLuceRating as Rating
from helpers.datehelper import strftime_ordinal
from db.types import Team, IntRole, EventType, SM5_ENEMY_TEAM
from typing import List, Optional
from tortoise import Model, fields
from helpers.cachehelper import cache
import math
import sys

# The current version we expect in SM5Game.laserrank_version. If it doesn't match, that game should be migrated
# with the migrate_games action.
SM5_LASERRANK_VERSION = 3


class SM5Game(Model):
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
    mission_duration = fields.IntField()  # in milliseconds
    log_time = fields.DatetimeField(auto_now_add=True)
    # Field that is not currently stored: penalty (the amount of points deducted from when a player gets a penalty ex: 0, -1000)
    teams = fields.ManyToManyField("models.Teams")
    entity_starts = fields.ManyToManyField("models.EntityStarts")
    events = fields.ManyToManyField("models.Events")
    player_states = fields.ManyToManyField("models.PlayerStates")
    scores = fields.ManyToManyField("models.Scores")
    entity_ends = fields.ManyToManyField("models.EntityEnds")
    sm5_stats = fields.ManyToManyField("models.SM5Stats")
    # If not null, this is the team that eliminated the other.
    last_team_standing = fields.CharEnumField(Team, null=True)
    # Our internal SM5 game version when this game was imported. If it doesn't match SM5_LASERRANK_VERSION, it
    # should be recomputed/migrated.
    laserrank_version = fields.IntField(default=0)
    # Number of players on the first team.
    team1_size = fields.IntField(null=True)
    # Number of players on the second team.
    team2_size = fields.IntField(null=True)

    def __str__(self) -> str:
        return f"SM5Game ({self.start_time})"

    def __repr__(self) -> str:
        return f"<SM5Game ({self.tdf_name})>"

    async def get_team_score(self, team: Team) -> int:
        # Add 10,000 extra points if this team eliminated the opposition.
        adjustment = self.get_team_score_adjustment(team)
        return adjustment + sum(map(lambda x: x[0],
                                    await self.entity_ends.filter(entity__team__color_name=team.element).values_list(
                                        "score")))

    def get_team_score_adjustment(self, team: Team) -> int:
        """Returns how many points should be added to the team score in addition to the sum of the players' scores."""
        # The only adjustment currently is the 10k bonus for a team that eliminates another team.
        return 10000 if team == self.last_team_standing else 0

    def get_unranked_reason_tooltip(self) -> Optional[str]:
        """
        Returns the reason why this game is unranked, if it is.
        
        Returns None if the game is ranked or if there is no reason for it to be unranked.
        """

        # TODO: could use an enum?
        if not self.ranked:
            if self.ended_early:
                return "unranked_reason_ended_early"
            elif self.team1_size < 5 or self.team2_size < 5:
                return "unranked_reason_too_small"
            elif self.team1_size > 7 or self.team2_size > 7:
                return "unranked_reason_too_large"
            elif self.team1_size != self.team2_size:
                return "unranked_reason_unbalanced"
            else:
                return "unranked_reason_unknown"
        return None


    async def get_entity_start_from_token(self, token: str) -> Optional["EntityStarts"]:
        return await self.entity_starts.filter(entity_id=token).first()

    async def get_entity_end_from_token(self, token: str) -> Optional["EntityEnds"]:
        return await self.entity_ends.filter(entity_id=token).first()

    async def get_entity_start_from_name(self, name: str) -> Optional["EntityStarts"]:
        return await self.entity_starts.filter(name=name).first()

    async def get_entity_end_from_name(self, name: str) -> Optional["EntityEnds"]:
        return await self.entity_ends.filter(entity__name=name).first()

    async def get_sm5_stat_from_name(self, name: str) -> Optional["SM5Stats"]:
        return await self.sm5_stats.filter(entity__name=name).first()

    async def get_entity_score_at_time(self, entity_id: int, time_seconds: int) -> int:
        scores = await self.scores.filter(time__lte=time_seconds, entity=entity_id).all()

        return scores[-1].new if scores else 0

    async def get_actual_game_duration(self) -> int:
        """Returns the actual mission duration time in milliseconds.

        Returns the expected duration time unless the game terminated early, for example because one entire team was
        eliminated."""
        end_event = await self.events.filter(type=EventType.MISSION_END).first()

        return end_event.time if end_event else self.mission_duration

    # funcs for getting total score at a certain time for a team

    async def get_team_score_at_time(self, team: Team, time: int) -> int:  # time in seconds
        return sum(map(lambda x: x[0],
                       await self.scores.filter(time__lte=time, entity__team__color_name=team.element).values_list(
                           "delta")))

    # funcs for getting win chance and draw chance

    @cache()
    async def get_win_chance(self) -> List[float]:
        """
        Returns the win chance in the format [red, green]
        """
        from helpers.ratinghelper import MU, SIGMA

        # get the win chance for red team
        # this is based on the most current elo of the player's entity_end

        # get all the entity_ends for the red team

        entity_ends_red = await self.entity_ends.filter(entity__team__color_name="Fire", entity__type="player")

        # get the elo for each player

        elos_red = []

        for entity_end in entity_ends_red:
            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                elos_red.append(Rating(MU, SIGMA))
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
                elos_green.append(Rating(MU, SIGMA))
            else:
                player = await entity_end.get_player()
                elos_green.append(Rating(player.sm5_mu, player.sm5_sigma))

        # get the win chance

        from helpers.ratinghelper import model
        return model.predict_win([elos_red, elos_green])

    @cache()
    async def get_win_chance_before_game(self) -> List[float]:
        """
        Returns the win chance as guessed before the game happened in the format [red, green]
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

        entity_ends_green = await self.entity_ends.filter(entity__team__color_name="Earth", entity__type="player")

        # get the previous elo for each player

        previous_elos_green = []
        for entity_end in entity_ends_green:
            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                previous_elos_green.append(Rating(MU, SIGMA))
            else:
                previous_elos_green.append(Rating(entity_end.previous_rating_mu, entity_end.previous_rating_sigma))

        # double check if elo is None or not

        for i, elo in enumerate(previous_elos_red + previous_elos_green):
            if elo is None or elo.mu is None or elo.sigma is None:
                if i < len(previous_elos_red):
                    previous_elos_red[i] = Rating(MU, SIGMA)
                else:
                    previous_elos_green[i - len(previous_elos_red)] = Rating(MU, SIGMA)

        # get the win chance

        from helpers.ratinghelper import model
        return model.predict_win([previous_elos_red, previous_elos_green])

    @cache()
    async def get_win_chance_after_game(self) -> List[float]:
        """
        Returns the win chance as guessed **directly** after the game happened in the format [red, green]
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

        entity_ends_green = await self.entity_ends.filter(entity__team__color_name="Earth", entity__type="player")

        # get the current_elo for each player

        current_elos_green = []
        for entity_end in entity_ends_green:
            if (await entity_end.entity).entity_id.startswith("@"):
                # non-member player
                current_elos_green.append(Rating(MU, SIGMA))
            else:
                current_elos_green.append(Rating(entity_end.current_rating_mu, entity_end.current_rating_sigma))

        # double check if elo is None or not

        for i, elo in enumerate(current_elos_red + current_elos_green):
            if elo is None or elo.mu is None or elo.sigma is None:
                if i < len(current_elos_red):
                    current_elos_red[i] = Rating(MU, SIGMA)
                else:
                    current_elos_green[i - len(current_elos_red)] = Rating(MU, SIGMA)

        # get the win chance

        from helpers.ratinghelper import model
        return model.predict_win([current_elos_red, current_elos_green])

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

    async def get_team_eliminated(self, team: Team) -> bool:
        """
        Returns True if the other team was eliminated
        """

        players_alive_on_team = await self.entity_starts \
            .filter(team__color_name=team.element) \
            .filter(type="player", sm5statss__lives_left__gt=0) \
            .count()  # count the number of players on the red team that are still alive

        return players_alive_on_team == 0

    async def to_dict(self, full: bool = True, player_stats=None) -> dict:
        # convert the entire game to a dict
        # this is used for the api

        await self.fetch_related("teams", "entity_starts", "events", "player_states", "scores", "entity_ends",
                                 "sm5_stats")

        final = {}

        final["id"] = self.id
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
        final["sm5_stats"] = [await sm5_stat.to_dict() for sm5_stat in self.sm5_stats]

        if player_stats is not None:
            final["player_entity_start"] = await (
                await self.get_entity_start_from_name(player_stats.codename)).to_dict()
            final["player_entity_end"] = await (await self.get_entity_end_from_name(player_stats.codename)).to_dict()
            final["player_sm5_stats"] = await (await self.get_sm5_stat_from_name(player_stats.codename)).to_dict()

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

    async def mvp_points(self) -> float:
        """
        mvp points according to lfstats.com

        NOTE: this is a function, while LaserballStats.mvp_points is a property
        """

        score: int = await (await self.entity).get_score()
        game: SM5Game = await SM5Game.filter(entity_starts__id=(await self.entity).id).first()

        total_points = 0

        # accuracy: .1 point for every 1% of accuracy, rounded up

        accuracy = (self.shots_hit / self.shots_fired) if self.shots_fired != 0 else 0
        total_points += math.ceil(accuracy * 10)

        # medic hits: 1 point for every medic hit, -1 for your own medic hits

        total_points += self.medic_hits - self.own_medic_hits

        # elims: minimum 4 points if your team eliminates the other team, increased by 1/60 for each of second of game time remaining above 3 minutes.
        # ^ UPDATE: changed by the committee to from 1 point for every 60 seconds of game time above 1 minute.

        # check if team eliminated the other team

        mission_end = await game.events.filter(type=EventType.MISSION_END).first()

        if mission_end is not None:
            mission_length = mission_end.time

            if await game.get_team_eliminated(SM5_ENEMY_TEAM[(await (await self.entity).team).enum]):
                total_points += round(max(4, 4 + (game.mission_duration - mission_length - 180 * 1000) / 1000 / 60), 2)

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

    @cache()
    async def to_dict(self) -> dict:
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
