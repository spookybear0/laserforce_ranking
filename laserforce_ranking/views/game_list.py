from laserforce_ranking.models import SITES, Game, ID_TO_SITE
from django.views.generic import ListView
from django.shortcuts import render
import random
from django.core.paginator import Paginator

def get_games(request, player_entity_id=None):
    sort_by = request.GET.get("sort", "start_time")
    game_type = request.GET.get("mode", "sm5")
    print(f"Sort by: {sort_by}, Game type: {game_type}, Player entity ID: {player_entity_id}")

    if not player_entity_id and request.GET.get("player"):
        player_entity_id = request.GET.get("player")

    allowed_fields = {
        "start_time": "start_time",
        "-start_time": "-start_time",
        "site": "site",
        "-site": "-site",
        "duration": "duration",
        "-duration": "-duration",
        "outcome": "outcome",
        "-outcome": "-outcome",
        "score": "score",
        "-score": "-score",
    }

    db_field = allowed_fields.get(sort_by, "start_time")

    games = Game.objects.all()

    # Player filter
    if player_entity_id:
        games = games.filter(
            entity_ends__entity__entity_id=player_entity_id
        ).distinct()

    # Site filter
    site = request.GET.get("site")
    if site:
        games = games.filter(site_id=SITES[site])

    return games.order_by(db_field)


def get_game_table_context(request, player_entity_id=None):
    games = get_games(request, player_entity_id)

    paginator = Paginator(games, 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return {
        "games": page_obj.object_list,
        "page_obj": page_obj,
        "current_sort": request.GET.get("sort", "start_time"),
        "sites": SITES,
        "id_to_site": ID_TO_SITE,
        "current_page": request.GET.get("page", 1),
        "current_site": request.GET.get("site"),
        "current_mode": request.GET.get("mode", "sm5"),
        "player_entity_id": player_entity_id,
    }

class GameListView(ListView):
    template_name = "game_list.html"
    context_object_name = "games"
    paginate_by = 10  # Adjust as needed

    def get_queryset(self):
        return get_games(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            get_game_table_context(self.request)
        )
        context["games"] = [game for game in context["games"]]
        return context

    def render_to_response(self, context, **response_kwargs):
        # Intercept HTMX requests to return only the partial fragment
        if self.request.htmx:
            self.template_name = "partials/game_table.html"
        return super().render_to_response(context, **response_kwargs)