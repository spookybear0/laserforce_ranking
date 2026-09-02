from django.templatetags.static import static
from django.urls import reverse
from jinja2 import Environment
from .models.types import SITES, ID_TO_SITE, COMPETITIVE_SITES, SITE_TIMEZONES, IPL_NAME_TO_SITE_ID, IntRole
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
        }
    )

    return env