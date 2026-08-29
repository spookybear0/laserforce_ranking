from django.views import View
from django.views.generic.detail import DetailView
from django.shortcuts import render
from laserforce_ranking.models import Game
from laserforce_ranking.models import SITES

class GameView(DetailView):
    model = Game
    template_name = "game.html"
    context_object_name = "game"

    def get_object(self, queryset=None):
        """
        Override get_object to fetch the player based on the provided ID.
        """
        print(f"Fetching game with tdf_name: {self.kwargs.get('tdf_name')}")  # Debugging output
        tdf_name = self.kwargs.get("tdf_name")
        return Game.objects.get(tdf_name=tdf_name)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context