from django.db import models
from types import Permission

"""
Player.ratings specification:
[
    "general": {
        "sm5_mu": float,
        "sm5_sigma": float,
        "commander_mu": float,
        "commander_sigma": float,
        "heavy_mu": float,
        "heavy_sigma": float,
        "scout_mu": float,
        "scout_sigma": float,
        "ammo_mu": float,
        "ammo_sigma": float,
        "medic_mu": float,
        "medic_sigma": float,
        "laserball_mu": float,
        "laserball_sigma": float,
    }
    arena_id(int): {
        "sm5_mu": float,
        "sm5_sigma": float,
        "commander_mu": float,
        "commander_sigma": float,
        "heavy_mu": float,
        "heavy_sigma": float,
        "scout_mu": float,
        "scout_sigma": float,
        "ammo_mu": float,
        "ammo_sigma": float,
        "medic_mu": float,
        "medic_sigma": float,
        "laserball_mu": float,
        "laserball_sigma": float,
    }
    ... (for every arena played in)
}
"""

class Player(models.Model):
    entity_id = models.CharField(max_length=15, unique=True)
    codename = models.CharField(max_length=50)
    player_id = models.CharField(max_length=50, unique=True)
    ratings = models.JSONField(default=dict)

    # general db stuff

    timestamp = models.DatetimeField(auto_now=True)

    # account stuff
    password = models.CharField(max_length=255, null=True)  # hashed password
    permissions = models.IntegerField(choices=Permission, default=Permission.USER)

    # TODO: rfid

    def __str__(self):
        return self.name