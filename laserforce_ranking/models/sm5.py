from django.db import models
from .game import Game, Team
from .types import TeamType, IntRole, EventType, SM5_ENEMY_TEAM, ID_TO_SITE
from typing import Optional
from asgiref.sync import sync_to_async
import math

class SM5Stats(models.Model):
    game = models.ForeignKey("SM5Game", on_delete=models.CASCADE, related_name="sm5_stats")
    entity = models.ForeignKey("EntityStart", on_delete=models.CASCADE)
    entity_end = models.ForeignKey("EntityEnd", on_delete=models.CASCADE)
    shots_hit = models.PositiveSmallIntegerField()
    shots_fired = models.PositiveSmallIntegerField()
    times_zapped = models.PositiveSmallIntegerField()
    times_missiled = models.PositiveSmallIntegerField()
    missile_hits = models.PositiveSmallIntegerField()
    nukes_detonated = models.PositiveSmallIntegerField()
    nukes_activated = models.PositiveSmallIntegerField()
    nuke_cancels = models.PositiveSmallIntegerField()
    medic_hits = models.PositiveSmallIntegerField()
    own_medic_hits = models.PositiveSmallIntegerField()
    medic_nukes = models.PositiveSmallIntegerField()
    scout_rapid_fires = models.PositiveSmallIntegerField()
    life_boosts = models.PositiveSmallIntegerField()
    ammo_boosts = models.PositiveSmallIntegerField()
    lives_left = models.PositiveSmallIntegerField()
    shots_left = models.PositiveSmallIntegerField()
    penalties = models.PositiveSmallIntegerField()
    shot_3_hits = models.PositiveSmallIntegerField()
    own_nuke_cancels = models.PositiveSmallIntegerField()
    shot_opponent = models.PositiveSmallIntegerField()
    shot_team = models.PositiveSmallIntegerField()
    missiled_opponent = models.PositiveSmallIntegerField()
    missiled_team = models.PositiveSmallIntegerField()

    # custom addition that's not in the tdf
    special_points = models.PositiveSmallIntegerField(null=True) # add after game save

    @property
    def bases_destroyed(self) -> int:
        # get last digit of score from entity_end
        score = self.entity_end.score
        return int(str(score)[-1]) if score is not None else 0
    
    @property
    def mvp_points(self) -> float:
        """
        mvp points according to lfstats.com

        NOTE: this is a function, while LaserballStats.mvp_points is a property
        """

        entity = self.entity
        entity.team
        entity_end = self.entity_end

        score: int = entity_end.score
        game: SM5Game = SM5Game.objects.filter(entity_starts__id=entity.id).prefetch_related("last_team_standing").first()

        total_points = 0

        # accuracy: .1 point for every 1% of accuracy

        accuracy = (self.shots_hit / self.shots_fired) if self.shots_fired != 0 else 0
        total_points += round(accuracy * 10)

        # medic hits: 1 point for every medic hit, -1 for your own medic hits

        total_points += self.medic_hits - self.own_medic_hits

        # elims: minimum 4 points if your team eliminates the other team, increased by 1/60 for each of second of game time remaining above 3 minutes.
        # ^ UPDATE: changed by the committee to from 1 point for every 60 seconds of game time above 1 minute.

        # check if team eliminated the other team

        mission_end = game.events.filter(type=EventType.MISSION_END).first()

        if mission_end is not None:
            mission_length = mission_end.time

            last_team_standing = game.last_team_standing

            if last_team_standing and last_team_standing.name == entity.team.name:
                total_points += round(max(4, 4 + (game.mission_duration.total_seconds() - mission_length / 1000 - 180) / 60), 2)

        # cancel opponent nukes: 3 points for every opponent nuke canceled

        total_points += self.nuke_cancels * 3

        # cancel own nukes: -3 points for every own nuke canceled

        total_points -= self.own_nuke_cancels * 3

        # get missiled: -1 point for every time you get missiled

        total_points -= self.times_missiled

        # get eliminated: -1 point for getting elimated (doesn't apply to medics)

        if self.lives_left <= 0 and entity.role != IntRole.MEDIC:
            total_points -= 1

        # commander specific points:

        if entity.role == IntRole.COMMANDER:
            # missile opponent: 1 point for every missile on an opponent

            total_points += self.missiled_opponent

            # nukes: 1 point for every nuke detonated

            total_points += self.nukes_detonated

            # score bonus: 1 point (fractionally) for every 1000 points of score over 10000

            if score > 10000:
                total_points += (score - 10000) / 1000

        # heavy specific points:
        elif entity.role == IntRole.HEAVY:
            # missiles: 2 points for every missile hit

            total_points += self.missiled_opponent * 2

            # score bonus: 1 point (fractionally) for every 1000 points of score over 7000

            if score > 7000:
                total_points += (score - 7000) / 1000

        # scout specific points:
        elif entity.role == IntRole.SCOUT:
            # hits vs 3 hit (commander/heavy): .2 points for every hit vs 3 hit

            total_points += self.shot_3_hits * .2

            # score bonus: 1 point (fractionally) for every 1000 points of score over 6000

            if score > 6000:
                total_points += (score - 6000) / 1000

        # ammo specific points:
        elif entity.role == IntRole.AMMO:
            # ammo boosts: 3 point for every ammo boost

            total_points += self.ammo_boosts * 3

            # score bonus: 1 point (fractionally) for every 1000 points of score over 5000

            if score > 3000:
                total_points += (score - 3000) / 1000

        # medic specific points:
        elif entity.role == IntRole.MEDIC:
            # life boosts: 3 points for every life boost

            total_points += self.life_boosts * 3

            # survival bonus: 2 points for being alive at the end of the game

            if self.lives_left > 0:
                total_points += 2

            # score bonus: 2 points (fractionally) for every 1000 points of score over 2000

            if score > 2000:
                total_points += ((score - 2000) / 1000) * 2

        return total_points
    
    @property
    def kd_ratio(self) -> float:
        return self.shot_opponent / self.times_zapped if self.times_zapped != 0 else math.inf

    @property
    def accuracy(self) -> float:
        return self.shots_hit / self.shots_fired if self.shots_fired != 0 else 0
    
    @property
    def medic_hits_str(self) -> str:
        """Returns the medic hits in the format that is used by LaserForce.

        This is shown as medic_hits_by_tagging_and_missiling/medic_hits_by_nuking/own_medic_hits

        Example: 3/6/-1 (3 hits through tags/missiles, 2 nukes, one tag on the own medic)

        Any component that is 0 will not be shown (except for the first one, which is always shown).
        """
        nuke_hits_str = f"/{self.medic_nukes}" if self.medic_nukes else ""
        own_medic_hits_str = f"/-{self.own_medic_hits}" if self.own_medic_hits else ""
        return f"{self.medic_hits}{nuke_hits_str}{own_medic_hits_str}"

    def __str__(self):
        return f"SM5Stats for {self.entity} in game {self.entity.game}"
    
    class Meta:
        verbose_name = "SM5 stat"
        verbose_name_plural = "SM5 stats"

class SM5Game(Game):
    # SM5 specific fields

    # sm5_stats is a related name for SM5Stats, which is a one-to-many relationship with SM5Game

    last_team_standing = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name="last_team_standing")
    rank_version = models.PositiveSmallIntegerField(default=0)

    @property
    def short_type(self) -> str:
        return "sm5"

    def get_team_score_adjustment(self, team: Team) -> int:
        """Returns how many points should be added to the team score in addition to the sum of the players' scores."""
        # The only adjustment currently is the 10k bonus for a team that eliminates another team.
        return 10000 if team == self.last_team_standing else 0
    
    def get_team_score_adjustment_str(self, team: TeamType) -> str:
        """Returns a string explaining how many points should be added to the team score in addition to the sum of the players' scores."""
        adjustment = self.get_team_score_adjustment(team)
        if adjustment == 0:
            return ""
        elif adjustment > 0:
            return f" (+{adjustment})"
        else:
            return f" ({adjustment})"
    
    # get_unranked_reason():

    async def get_teams(self) -> tuple[Team, Team]:
        """Returns the two teams in the game. This excludes the neutral team"""
        teams = [team async for team in self.teams.exclude(name="Neutral").exclude(color_enum=0).all()]
        return teams[0], teams[1]

    async def get_medic_death_time(self, team: TeamType) -> Optional[int]:
        """
        Returns the time in milliseconds when the medic on the given team died, or None if they never died.
        """

        # this will find when the medic entity is finished
        # which if it's before the end of the mission, means the medic died
        # filter by team and role (medic)
        medic_death_event = await self.entity_ends \
            .filter(entity__team=team, entity__role=IntRole.MEDIC) \
            .afirst()

        if medic_death_event and medic_death_event.time < self.duration.seconds * 1000:
            return medic_death_event.time
        return None
    
    async def _get_team_doubles_percent(self, team: TeamType) -> float:
        """
        Gets how well a team did doubles while medic is still alive.

        This should only be used once on game import
        """

        # get what timestamp the medic died at

        medic_death_time = await self.get_medic_death_time(team)

        # go through every resupply
        resupplies = [event async for event in self.events \
            .filter(type__in=[EventType.RESUPPLY_AMMO, EventType.RESUPPLY_LIVES]) \
            .filter(
                time__lte=medic_death_time if medic_death_time is not None else self.mission_duration.total_seconds() * 1000
            ).all()]

        groups = {}

        for resupply in resupplies:
            entity1 = await self.entity_starts.filter(entity_id=resupply.entity1).afirst()
            from asgiref.sync import sync_to_async
            entity1_team = await sync_to_async(lambda: entity1.team)()

            if entity1_team.name != team.name:
                continue

            target = resupply.entity2

            if target not in groups:
                groups[target] = [{
                    "start": resupply.time,
                    "events": [resupply]
                }]
                continue

            current = groups[target][-1]

            if resupply.time - current["start"] <= 3000:
                current["events"].append(resupply)
            else:
                groups[target].append({
                    "start": resupply.time,
                    "events": [resupply]
                })

        total = 0
        double_events = 0

        for target_groups in groups.values():
            for group in target_groups:
                count = len(group["events"])

                total += count

                if count >= 2:
                    double_events += count

        #logger.debug(f"Team {team.name} had {double_events} double events out of {total} total events")

        return double_events / total if total > 0 else 0
    
    def __str__(self):
        return f"SM5Game {self.id} at {ID_TO_SITE.get(self.site_id, self.site_id)} on {self.start_time}"
    
    class Meta:
        verbose_name = "SM5 game"
        verbose_name_plural = "SM5 games"