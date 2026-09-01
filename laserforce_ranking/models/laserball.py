from django.db import models

class LaserballStats(models.Model):
    game = models.ForeignKey("Game", on_delete=models.CASCADE, related_name="laserball_stats")
    entity = models.ForeignKey("EntityStart", on_delete=models.CASCADE)
    goals = models.PositiveSmallIntegerField()
    assists = models.PositiveSmallIntegerField()
    passes = models.PositiveSmallIntegerField()
    steals = models.PositiveSmallIntegerField()
    clears = models.PositiveSmallIntegerField()
    blocks = models.PositiveSmallIntegerField()
    shots_fired = models.PositiveSmallIntegerField()
    shots_hit = models.PositiveSmallIntegerField()
    started_with_ball = models.PositiveSmallIntegerField()
    times_stolen = models.PositiveSmallIntegerField()
    times_blocked = models.PositiveSmallIntegerField()
    passes_received = models.PositiveSmallIntegerField()

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
        return (self.goals + self.assists) * 10000 + min(self.steals, 99) * 100 + min(self.blocks, 99)

    def __str__(self):
        return f"LaserballStats for {self.entity}"
    
    class Meta:
        verbose_name = "Laserball stat"
        verbose_name_plural = "Laserball stats"