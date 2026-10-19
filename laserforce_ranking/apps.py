from django.apps import AppConfig
from asgiref.sync import async_to_sync
import os
import sys


async def startup():
    if "makemigrations" in sys.argv or "migrate" in sys.argv:
        return
    from laserforce_ranking.tdf import import_legacy_tdf, download_tdfs, mass_parse_tdfs
    #await download_tdfs(site_id="4-19", game_type="sm5")
    #await mass_parse_tdfs()

class LaserforceRankingConfig(AppConfig):
    name = "laserforce_ranking"

    def ready(self):
        if os.environ.get("RUN_MAIN") == "true" or not os.environ.get("RUN_MAIN"):
            async_to_sync(startup)()