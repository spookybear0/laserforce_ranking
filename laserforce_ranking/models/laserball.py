from django.db import models

class LaserballStats(models.Model):
    entity = models.ForeignKey("EntityStart", on_delete=models.CASCADE)
    goals = models.IntegerField()
    assists = models.IntegerField()
    passes = models.IntegerField()
    steals = models.IntegerField()
    clears = models.IntegerField()
    blocks = models.IntegerField()
    shots_fired = models.IntegerField()
    shots_hit = models.IntegerField()
    started_with_ball = models.IntegerField()
    times_stolen = models.IntegerField()
    times_blocked = models.IntegerField()
    passes_received = models.IntegerField()

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
