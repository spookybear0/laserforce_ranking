from django.db import models
from .game import Game, Team
from .types import TeamType, IntRole, EventType, SM5_ENEMY_TEAM
from typing import Optional
from asgiref.sync import sync_to_async
import math

class SM5Stats(models.Model):
    entity = models.ForeignKey("EntityStart", on_delete=models.CASCADE)
    entity_end = models.ForeignKey("EntityEnd", on_delete=models.CASCADE)
    shots_hit = models.IntegerField()
    shots_fired = models.IntegerField()
    times_zapped = models.IntegerField()
    times_missiled = models.IntegerField()
    missile_hits = models.IntegerField()
    nukes_detonated = models.IntegerField()
    nukes_activated = models.IntegerField()
    nuke_cancels = models.IntegerField()
    medic_hits = models.IntegerField()
    own_medic_hits = models.IntegerField()
    medic_nukes = models.IntegerField()
    scout_rapid_fires = models.IntegerField()
    life_boosts = models.IntegerField()
    ammo_boosts = models.IntegerField()
    lives_left = models.IntegerField()
    shots_left = models.IntegerField()
    penalties = models.IntegerField()
    shot_3_hits = models.IntegerField()
    own_nuke_cancels = models.IntegerField()
    shot_opponent = models.IntegerField()
    shot_team = models.IntegerField()
    missiled_opponent = models.IntegerField()
    missiled_team = models.IntegerField()

    # custom addition that's not in the tdf
    special_points = models.IntegerField(null=True) # add after game save

    @property
    def bases_destroyed(self) -> int:
        # get last digit of score from entity_end
        score = self.entity_end.score
        return int(str(score)[-1]) if score is not None else 0
    
    async def mvp_points(self) -> float:
        """
        mvp points according to lfstats.com

        NOTE: this is a function, while LaserballStats.mvp_points is a property
        """

        entity = await sync_to_async(lambda: self.entity)()
        entity_end = await sync_to_async(lambda: self.entity_end)()

        score: int = entity_end.score
        game: SM5Game = await SM5Game.filter(entity_starts__id=entity.id).afirst()

        total_points = 0

        # accuracy: .1 point for every 1% of accuracy, rounded up

        accuracy = (self.shots_hit / self.shots_fired) if self.shots_fired != 0 else 0
        total_points += math.ceil(accuracy * 10)

        # medic hits: 1 point for every medic hit, -1 for your own medic hits

        total_points += self.medic_hits - self.own_medic_hits

        # elims: minimum 4 points if your team eliminates the other team, increased by 1/60 for each of second of game time remaining above 3 minutes.
        # ^ UPDATE: changed by the committee to from 1 point for every 60 seconds of game time above 1 minute.

        # check if team eliminated the other team

        mission_end = await game.events.filter(type=EventType.MISSION_END).afirst()

        if mission_end is not None:
            mission_length = mission_end.time

            if game.last_team_standing.name == entity.team.name:
                total_points += round(max(4, 4 + (game.mission_duration - mission_length - 180 * 1000) / 1000 / 60), 2)

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

            # nukes canceled: -1 point for every nuke that you activated that was canceled

            total_points -= self.own_nuke_cancels

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

class SM5Game(Game):
    sm5_stats = models.ManyToManyField(SM5Stats)
    last_team_standing = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name="last_team_standing")
    rank_version = models.IntegerField(default=0)

    # precalculatead percentage of doubles (resupplies within 3 seconds to the same target) for each team,
    # since this is a costly calculation and we want to show it on the game page
    team1_double_percent = models.FloatField(null=True)
    team2_double_percent = models.FloatField(null=True)

    def get_team_score_adjustment(self, team: TeamType) -> int:
        """Returns how many points should be added to the team score in addition to the sum of the players' scores."""
        # The only adjustment currently is the 10k bonus for a team that eliminates another team.
        return 10000 if team == self.last_team_standing else 0
    
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

        if medic_death_event and medic_death_event.time < await self.get_game_duration():
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
                time__lte=medic_death_time if medic_death_time is not None else self.mission_duration
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