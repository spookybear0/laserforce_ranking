from django.db import models

class LaserballStats(models.Model):
    entity = models.ForeignKey("EntityStart", on_delete=models.CASCADE)
    goals = models.IntField()
    assists = models.IntField()
    passes = models.IntField()
    steals = models.IntField()
    clears = models.IntField()
    blocks = models.IntField()
    shots_fired = models.IntField()
    shots_hit = models.IntField()
    started_with_ball = models.IntField()
    times_stolen = models.IntField()
    times_blocked = models.IntField()
    passes_received = models.IntField()

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
