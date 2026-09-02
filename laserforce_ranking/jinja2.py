from django.templatetags.static import static
from django.urls import reverse
from jinja2 import Environment
from .models import Player
from .models.types import SITES, ID_TO_SITE, COMPETITIVE_SITES, SITE_TIMEZONES, IPL_NAME_TO_SITE_ID, IntRole, EntityType
from django.db.models import Sum, Avg
from asgiref.sync import sync_to_async
import os

if os.name == "nt":
    day_no_leading_zero = "%#d"
else:
    day_no_leading_zero = "%-d"

def environment(**options):
    """Configures the Jinja2 environment with Django global functions."""
    env = Environment(**options, enable_async=True)

    # inject Django helper functions into Jinja2 templates
    env.globals.update(
        {
            "url": reverse,
            "static": static,
            "zip": zip,
            "day_no_leading_zero": day_no_leading_zero,
            "SITES": SITES,
            "ID_TO_SITE": ID_TO_SITE,
            "COMPETITIVE_SITES": COMPETITIVE_SITES,
            "SITE_TIMEZONES": SITE_TIMEZONES,
            "IPL_NAME_TO_SITE_ID": IPL_NAME_TO_SITE_ID,
            "IntRole": IntRole,
            "EntityType": EntityType,
            "Player": Player,
            "Sum": Sum,
            "Avg": Avg,
            "sync_to_async": sync_to_async,
        }
    )

    return env