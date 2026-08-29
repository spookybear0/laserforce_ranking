from django.db import models
from .types import Permission, IntRole, ID_TO_IPL_NAME
from .game import Game
from typing import Optional
from laserforce_ranking.rating import Rating

"""
Player.ratings specification:
[
    "global": {
        "sm5": {
            "mu": float,
            "sigma": float
        },
        "commander": {
            "mu": float,
            "sigma": float
        },
        "heavy": {
            "mu": float,
            "sigma": float
        },
        "scout": {
            "mu": float,
            "sigma": float
        },
        "ammo": {
            "mu": float,
            "sigma": float
        },
        "medic": {
            "mu": float,
            "sigma": float
        },
        "laserball": {
            "mu": float,
            "sigma": float
        }
    }
    site_id(int): {
        "sm5": {
            "mu": float,
            "sigma": float
        },
        "commander": {
            "mu": float,
            "sigma": float
        },
        "heavy": {
            "mu": float,
            "sigma": float
        },
        "scout": {
            "mu": float,
            "sigma": float
        },
        "ammo": {
            "mu": float,
            "sigma": float
        },
        "medic": {
            "mu": float,
            "sigma": float
        },
        "laserball": {
            "mu": float,
            "sigma": float
        }
    }
    ... (for every arena played in)
}
"""

class Player(models.Model):
    entity_id = models.CharField(max_length=15, unique=True)
    codename = models.CharField(max_length=50)
    player_id = models.CharField(max_length=50, unique=True, null=True) # iplaylaserforce player id
    ratings = models.JSONField(default=dict)
    # first site played at, found from iplaylaserforce
    home_site = models.CharField(max_length=50, null=True) # site id (ex: 4-43)

    # general db stuff

    timestamp = models.DateTimeField(auto_now_add=True)

    # account stuff
    password = models.CharField(max_length=255, null=True) # hashed password
    permissions = models.IntegerField(choices=Permission, default=Permission.USER)

    # TODO: rfid

    @property
    def home_site_name(self):
        if self.home_site is None:
            return "Unknown Site"
        return ID_TO_IPL_NAME.get(self.home_site, self.home_site)
    
    async def get_game_count(self, site: Optional[str] = None):
        """
        Get the number of games played by the player, optionally filtered by site.
        """
        
        if site is None:
            return await Game.objects.filter(entityend__entity__entity_id=self.entity_id).acount()
        else:
            return await Game.objects.filter(entityend__entity__entity_id=self.entity_id, site_id=site).acount()

    async def get_rating(self, game_type: str="sm5", role: Optional[IntRole]=None, site: Optional[str]=None):
        """
        Get specified rating from the player.ratings json object
        """

        key_1 = "global"

        if site is not None:
            key_1 = site

        if role is None:
            key_2 = game_type.lower()
        else:
            key_2 = role.name.lower()
       
        mu = self.ratings[key_1][key_2]["mu"]
        sigma = self.ratings[key_1][key_2]["sigma"]

        return Rating(mu, sigma)
        

    def __str__(self):
        return self.codename