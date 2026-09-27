from django.views import View
from django.shortcuts import render
from laserforce_ranking.models import SITE_BY_ID
from pathlib import Path
from laserforce_ranking.views.games import get_game_table_context
from django.http import Http404

class SiteView(View):
    def get(self, request, site_id):
        """
        Handle GET requests for the site page.
        """

        site = SITE_BY_ID.get(site_id, None)

        if not site:
            raise Http404("Site not found.")

        context = {
            "site": site,
        }

        context.update(get_game_table_context(request, site_id=site_id))

        return render(request, "site.html", context)