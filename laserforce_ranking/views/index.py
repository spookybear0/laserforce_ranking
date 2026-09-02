from django.views import View
from django.shortcuts import render
from laserforce_ranking.models import Player, Game

class IndexView(View):
    def get(self, request):
        """
        Handle GET requests for the index page.
        """

        
        return render(request, "index.html", context={
            "total_players": Player.objects.count(),
            "total_ranked_games": Game.objects.filter(ranked=True).count(),
            

        })