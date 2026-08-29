from django.views import View
from django.views.generic.detail import DetailView
from django.shortcuts import render
from laserforce_ranking.models import Player
from laserforce_ranking.models import SITES
from laserforce_ranking.views.game_list import get_game_table_context

class PlayerView(DetailView):
    model = Player
    template_name = "player.html"
    context_object_name = "player"

    def get_object(self, queryset=None):
        """
        Override get_object to fetch the player based on the provided ID.
        """
        print(f"Fetching player with ID: {self.kwargs.get('entity_id')}")  # Debugging output
        entity_id = self.kwargs.get("entity_id")

        entity_id = "#" + entity_id

        return Player.objects.get(entity_id=entity_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            get_game_table_context(
                self.request,
                self.object.entity_id,
            )
        )
        context["player_entity_id"] = self.object.entity_id

        return context