from laserforce_ranking.models import SITES, COMPETITIVE_SITES
from django.views.generic import ListView
from django.shortcuts import render
from django.db.models import F, Value, FloatField, ExpressionWrapper, Count, Q, OuterRef, Subquery, IntegerField
from django.db.models.functions import Coalesce
from laserforce_ranking.models import Player, Game
import random

class PlayerListView(ListView):
    model = Player
    template_name = "player_list.html"
    context_object_name = "players"
    paginate_by = 10  # Adjust as needed

    def get_queryset(self):
        sort_by = self.request.GET.get("sort", "-ratings")

        # Map allowed frontend parameters to model fields safely
        allowed_fields = {
            "codename": "codename",
            "-codename": "-codename",
            "home_site": "home_site",
            "-home_site": "-home_site",
            "ratings": "ratings",
            "-ratings": "-ratings",
            "games": "games",
            "-games": "-games",
        }

        db_field = allowed_fields.get(sort_by, "-ratings")

        site = "global" if self.request.GET.get("site", "") == "" else self.request.GET.get("site")

        if db_field in ["ratings", "-ratings"]:
            print(f"Sorting by rating, site: {site}")

            db_field = f"{db_field}__{site}"

        games = (
            Game.objects
            .filter(
                entityend__entity__entity_id=OuterRef("entity_id")
            )
        )

        if site and site != "global":
            games = games.filter(site_id=site)

        games = (
            games
            .values("entityend__entity__entity_id")
            .annotate(
                count=Count("id", distinct=True)
            )
            .values("count")
        )

        # depending on what mode is selected, show the appropriate rating
        # and let frontend access it using player.rating

        print(site)

        return Player.objects.annotate(
            rating=ExpressionWrapper(
                F(f"ratings__{site}__{self.request.GET.get('mode', 'sm5')}__mu") - \
                F(f"ratings__{site}__{self.request.GET.get('mode', 'sm5')}__sigma") * Value(3, output_field=FloatField()),
                output_field=FloatField()
            ),
            games=Coalesce(
                Subquery(games[:1], output_field=IntegerField()),
                Value(0)
            ),
        ).order_by(db_field)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass current sorting to the template to toggle direction
        context["current_sort"] = self.request.GET.get("sort", "-ratings")
        context["current_page"] = self.request.GET.get("page", 1)
        context["current_mode"] = self.request.GET.get("mode", "sm5")
        context["current_site"] = self.request.GET.get("site")
        context["sites"] = SITES
        context["competitive_sites"] = COMPETITIVE_SITES
        print(self.request.GET)
        return context

    def render_to_response(self, context, **response_kwargs):
        # Intercept HTMX requests to return only the partial fragment
        if self.request.htmx:
            self.template_name = "partials/player_table.html"
        print(context)
        return super().render_to_response(context, **response_kwargs)