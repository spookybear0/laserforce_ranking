from django.views import View
from django.views.generic.detail import DetailView
from django.shortcuts import render
from laserforce_ranking.models import Player, EntityStart, EntityEnd, IntRole
from laserforce_ranking.views.games import get_game_table_context
from asgiref.sync import async_to_sync

class PlayerView(DetailView):
    model = Player
    template_name = "player.html"
    context_object_name = "player"

    def get_object(self, queryset=None):
        """
        Override get_object to fetch the player based on the provided ID.
        """
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

        # for games in games, get the entity_start of this player in that game and add it to the context
        entity_info = []
        for game in context["games"]:
            entity_start = EntityStart.objects.filter(game=game, entity_id=self.object.entity_id).first()
            entity_end = EntityEnd.objects.filter(game=game, entity__entity_id=self.object.entity_id).first()

            team = entity_start.team

            info = {
                "entity_start": entity_start,
                "entity_end": entity_end,
                "team": team if entity_start else None,
                "won": game.winner == team if entity_start else None,
            }

            if game.ranked and entity_end:
                info.update({
                    "current_rating": async_to_sync(entity_end.get_rating)("current", use_site=False, consider_roles=False).ordinal(),
                    "previous_rating": async_to_sync(entity_end.get_rating)("previous", use_site=False, consider_roles=False).ordinal(),
                })

            entity_info.append(info)
        
        
        context["entity_info"] = entity_info
        context["player_entity_id"] = self.object.entity_id

        context["rating_progression_chart"] = {
            "labels": [game.start_time.strftime("%Y-%m-%d") for game in reversed(context["games"])],
            "data": [info.get("current_rating", None) for info in reversed(entity_info)],
        }

        get_rating = async_to_sync(self.object.get_rating)

        # TODO: allow selecting site, for now use global
        context["role_rating_chart"] = {
            "labels": ["Commander", "Heavy", "Scout", "Ammo", "Medic"],
            "data": [
                get_rating(site=None, role=IntRole.COMMANDER).ordinal(),
                get_rating(site=None, role=IntRole.HEAVY).ordinal(),
                get_rating(site=None, role=IntRole.SCOUT).ordinal(),
                get_rating(site=None, role=IntRole.AMMO).ordinal(),
                get_rating(site=None, role=IntRole.MEDIC).ordinal()
            ],
        }

        return context
    
    def render_to_response(self, context, **response_kwargs):
        # Intercept HTMX requests to return only the partial fragment
        if self.request.htmx:
            self.template_name = "partials/player_game_table.html"
        return super().render_to_response(context, **response_kwargs)