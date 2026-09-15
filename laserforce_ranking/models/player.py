from django.db import models
from .types import Permission, IntRole, SITE_BY_ID, GameType, Site
from .game import Game
from typing import Optional, Union
from laserforce_ranking.rating import Rating, MU, SIGMA
from django_enum import EnumField
from django.urls import reverse

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
    previous_codenames = models.JSONField(default=list) # list of previous codenames for AKA list
    player_id = models.SlugField(unique=True, null=True) # iplaylaserforce player id (ex: 4-43-1265)
    ratings = models.JSONField(default=dict)
    # where membership was created
    home_site_id = models.SlugField(null=True) # site id (ex: 4-43)

    # general db stuff

    timestamp = models.DateTimeField(auto_now_add=True)

    # account stuff
    password = models.CharField(max_length=255, null=True) # hashed password
    permissions = EnumField(Permission, default=Permission.USER)

    # TODO: rfid

    @property
    def home_site(self) -> Union[str, Site]:
        if site := SITE_BY_ID.get(self.home_site_id):
            return site
        else:
            return Site(
                id=self.home_site_id, name=self.home_site_id, ipl_name=self.home_site_id
            )
    
    async def get_game_count(self, site: Optional[str] = None):
        """
        Get the number of games played by the player, optionally filtered by site.
        """
        
        if site is None:
            return await Game.objects.filter(entityend__entity__entity_id=self.entity_id).acount()
        else:
            return await Game.objects.filter(entityend__entity__entity_id=self.entity_id, site_id=site).acount()

    async def get_rating(self, game_type: Optional[GameType]=GameType.SM5, site: Optional[str]=None, role: Optional[IntRole]=None):
        """
        Get specified rating from the player.ratings json object
        """

        key_1 = "global"

        if site is not None:
            key_1 = site

        if role is None:
            key_2 = game_type.value.lower()
        else:
            key_2 = role.name.lower()

        # check if site exists in ratings
        # if its not, return default rating
        if key_1 not in self.ratings:
            return Rating(MU, SIGMA)
       
        mu = self.ratings[key_1][key_2]["mu"]
        sigma = self.ratings[key_1][key_2]["sigma"]

        return Rating(mu, sigma)
    
    def get_all_ratings_formatted(self):
        """
        Get all ratings from the player.ratings json object and format them into a string

        Global ratings before site ratings

        roles in the order of: sm5, commander, heavy, scout, ammo, medic, laserball
        """

        ratings_str = ""

        type_order = ["sm5", "commander", "heavy", "scout", "ammo", "medic", "laserball"]

        # First, add global ratings
        if "global" in self.ratings:
            ratings_str += "Global:\n"
            for game_type in type_order:
                if game_type in self.ratings["global"]:
                    rating = self.ratings["global"][game_type]
                    game_type = "SM5" if game_type == "sm5" else game_type.capitalize()
                    ratings_str += f"  {game_type}: {round(Rating(rating['mu'], rating['sigma']).ordinal(), 3)}\n"

        # Then, add site-specific ratings
        for site, site_ratings in self.ratings.items():
            if site == "global":
                continue

            site_name = SITE_BY_ID.get(site, site).name if SITE_BY_ID.get(site) else site

            ratings_str += f"{site_name}:\n"
            for game_type in type_order:
                if game_type in site_ratings:
                    rating = site_ratings[game_type]
                    game_type = "SM5" if game_type == "sm5" else game_type.capitalize()
                    ratings_str += f"  {game_type}: {round(Rating(rating['mu'], rating['sigma']).ordinal(), 3)}\n"

        return ratings_str

        
    
    def get_absolute_url(self):
        return reverse("player_detail", kwargs={"entity_id": self.entity_id})

    def __str__(self):
        return f"Player {self.codename} ({self.entity_id}, {self.player_id})"