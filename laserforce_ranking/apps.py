from django.apps import AppConfig
from asgiref.sync import async_to_sync
import os
import sys


async def startup():
    if "makemigrations" in sys.argv or "migrate" in sys.argv:
        return
    from laserforce_ranking.tdf import import_legacy_tdf, scrape_lfstats_tdf, mass_parse_tdfs
    #await scrape_lfstats_tdf(site_id="4-19", page_start=82)
    #await mass_parse_tdfs()

class LaserforceRankingConfig(AppConfig):
    name = "laserforce_ranking"

    def ready(self):
        if os.environ.get("RUN_MAIN") == "true" or not os.environ.get("RUN_MAIN"):
            async_to_sync(startup)()