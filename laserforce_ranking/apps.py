from django.apps import AppConfig
from asgiref.sync import async_to_sync
import os
import asyncio


async def startup():
    from laserforce_ranking.tdf import import_legacy_tdf, scrape_lfstats_tdf, mass_parse_tdfs
    #await mass_parse_tdfs()

class LaserforceRankingConfig(AppConfig):
    name = "laserforce_ranking"

    def ready(self):
        if os.environ.get("RUN_MAIN") == "true" or not os.environ.get("RUN_MAIN"):
            async_to_sync(startup)()