from django.db import models
from .types import Permission, IntRole
from typing import Optional
from laserforce_ranking.rating import Rating

"""
Player.ratings specification:
[
    "global": {
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
    site_id(int): {
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

    timestamp = models.DateTimeField(auto_now_add=True)

    # account stuff
    password = models.CharField(max_length=255, null=True) # hashed password
    permissions = models.IntegerField(choices=Permission, default=Permission.USER)

    # TODO: rfid

    async def get_rating(self, game_type: str, role: Optional[IntRole], site: Optional[str]):
        """
        Get specified rating from the player.ratings json object
        """

        key_1 = "global"

        if site is not None:
            key_1 = site

        if role is None:
            key_2 = f"{game_type.lower()}_"
        else:
            key_2 = f"{role.name.lower()}_"
       
        mu = self.ratings[key_1][f"{key_2}_mu"]
        sigma = self.ratings[key_1][f"{key_2}_sigma"]

        return Rating(mu, sigma)
        

    def __str__(self):
        return self.codename