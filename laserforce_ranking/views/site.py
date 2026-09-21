from django.views import View
from django.shortcuts import render
from laserforce_ranking.models import SITE_BY_ID
from pathlib import Path

class SiteView(View):
    def get(self, request, site_id):
        """
        Handle GET requests for the site page.
        """

        site = SITE_BY_ID.get(site_id, None)

        context = {
            "site": site,
        }

        return render(request, "site.html", context)