from laserforce_ranking.models import SITE_BY_ID, Game, SM5Game, Team
from django.views.generic import ListView
from django.shortcuts import render
from django.db.models import Case, When, Value, CharField, F, Q, Max, Min, OuterRef, Subquery, IntegerField
import random
from django.core.paginator import Paginator

# team score subqueries

active_teams_subquery = Team.objects.filter(
    game=OuterRef("pk")
).exclude(
    color_enum=0
).annotate(
    adjusted_score=(
        F("score")
        + Case(
            # only do +10000 for sm5 games and if there's a last team standing and this team is the last team standing
            When(Q(game__sm5game__isnull=False) & Q(game__sm5game__last_team_standing_id=F("pk")), then=Value(10000)),
            default=Value(0),
            output_field=IntegerField()
        )
    )
)

highest_score_sub = active_teams_subquery.order_by("-adjusted_score").values("adjusted_score")[:1]
lowest_score_sub  = active_teams_subquery.order_by("adjusted_score").values("adjusted_score")[:1]

highest_name_sub  = active_teams_subquery.order_by("-adjusted_score").values("color_name")[:1]
lowest_name_sub   = active_teams_subquery.order_by("adjusted_score").values("color_name")[:1]

def get_games(request, player_entity_id=None):
    sort_by = request.GET.get("sort", "-start_time")
    game_type = request.GET.get("mode", "sm5")

    if not player_entity_id and request.GET.get("player"):
        player_entity_id = request.GET.get("player")

    allowed_fields = {
        "start_time": "start_time",
        "-start_time": "-start_time",
        "site": "site_id",
        "-site": "-site_id",
        "duration": "duration",
        "-duration": "-duration",
        "outcome": "outcome",
        "-outcome": "-outcome",
        "score": "score_difference",
        "-score": "-score_difference",
    }

    db_field = allowed_fields.get(sort_by, "-start_time")

    if game_type == "sm5":
        games = SM5Game.objects.annotate(
            high_score=Subquery(highest_score_sub),
            low_score=Subquery(lowest_score_sub),
            # team names
            high_score_team=Subquery(highest_name_sub),
            low_score_team=Subquery(lowest_name_sub),
        ).annotate(
            # this is just the difference
            score_difference=F("high_score") - F("low_score"),

            outcome=Case(
                # if there is no last team standing, outcome was based on score
                When(winner__isnull=False, then=Value("Draw")),
                When(last_team_standing__isnull=False, then=Value("Score")),
                When(last_team_standing__isnull=True, then=Value("Elimination")),
                default=Value("Unknown"),
                output_field=CharField()
            ),
        )
    else: # laserball
        games = Game.objects.annotate(
            high_score=Subquery(highest_score_sub),
            low_score=Subquery(lowest_score_sub),
            # team names
            high_score_team=Subquery(highest_name_sub),
            low_score_team=Subquery(lowest_name_sub),
        ).annotate(
            # this is just the difference
            score_difference=F("high_score") - F("low_score"),

            outcome=Case(
                When(winner__isnull=False, then=Value("Draw")),
                default=Value("Score"),
                output_field=CharField()
            )
        )


    # Player filter
    if player_entity_id:
        games = games.filter(
            entity_ends__entity__entity_id=player_entity_id
        ).distinct()

    # Site filter
    site = request.GET.get("site")
    if site:
        games = games.filter(site_id=SITE_BY_ID[site].id)

    return games.order_by(db_field)


def get_game_table_context(request, player_entity_id=None):
    games = get_games(request, player_entity_id)

    paginator = Paginator(games, 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return {
        "games": page_obj.object_list,
        "page_obj": page_obj,
        "current_sort": request.GET.get("sort", "-start_time"),
        "current_page": request.GET.get("page", 1),
        "current_site": request.GET.get("site"),
        "current_mode": request.GET.get("mode", "sm5"),
        "player_entity_id": player_entity_id,
    }

class GameListView(ListView):
    template_name = "games.html"
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