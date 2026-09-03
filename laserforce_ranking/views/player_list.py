from laserforce_ranking.models import SITES, COMPETITIVE_SITES
from django.views.generic import ListView
from django.shortcuts import render
from django.db.models import F, Value, FloatField, ExpressionWrapper, Count, Q, OuterRef, Subquery, IntegerField
from django.db.models.functions import Coalesce, Cast
from django.db.models.fields.json import KT
from laserforce_ranking.models import Player, Game
import logging

logger = logging.getLogger(__name__)

class PlayerListView(ListView):
    model = Player
    template_name = "player_list.html"
    context_object_name = "players"
    paginate_by = 10  # Adjust as needed

    def get_queryset(self):
        logger.debug("Fetching queryset for PlayerListView")
        sort_by = self.request.GET.get("sort", "-ratings")
        logger.debug(f"Sort parameter received: {sort_by}")

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
        logger.debug(f"Sorting by database field: {db_field}")

        site = "global" if self.request.GET.get("site", "") == "" else self.request.GET.get("site")
        logger.debug(f"Site parameter received: {site}")

        if db_field in ["ratings", "-ratings"]:
            db_field = f"{db_field}__{site}"
            logger.debug(f"Adjusted sorting field for site: {db_field}")

        games = (
            Game.objects
            .filter(
                entity_ends__entity__entity_id=OuterRef("entity_id")
            )
        )

        if site and site != "global":
            games = games.filter(site_id=site)
            logger.debug(f"Filtering games for site: {site}")

        games = (
            games
            .values("entity_ends__entity__entity_id")
            .annotate(
                count=Count("id", distinct=True)
            )
            .values("count")
        )
        logger.debug("Games subquery prepared")

        # depending on what mode is selected, show the appropriate rating
        # and let frontend access it using player.rating
    
        mode = self.request.GET.get("mode", "sm5")
        logger.debug(f"Mode parameter received: {mode}")

        queryset = Player.objects.annotate(
            rating=ExpressionWrapper(
                Cast(KT(f"ratings__{site}__{mode}__mu"), FloatField())
                - Cast(KT(f"ratings__{site}__{mode}__sigma"), FloatField()) * Value(3.0),
                output_field=FloatField(),
            ),
            games=Coalesce(
                Subquery(games[:1], output_field=IntegerField()),
                Value(0)
            ),
        ).order_by(db_field)
        logger.debug("Queryset annotated and ordered")
        return queryset

    def get_context_data(self, **kwargs):
        logger.debug("Fetching context data for PlayerListView")
        context = super().get_context_data(**kwargs)
        # Pass current sorting to the template to toggle direction
        context["current_sort"] = self.request.GET.get("sort", "-ratings")
        context["current_page"] = self.request.GET.get("page", 1)
        context["current_mode"] = self.request.GET.get("mode", "sm5")
        context["current_site"] = self.request.GET.get("site")
        context["sites"] = SITES
        context["competitive_sites"] = COMPETITIVE_SITES
        logger.debug(f"Context data prepared: {context}")
        return context

    def render_to_response(self, context, **response_kwargs):
        logger.debug("Rendering response for PlayerListView")
        # Intercept HTMX requests to return only the partial fragment
        if self.request.htmx:
            self.template_name = "partials/player_table.html"
            logger.debug("HTMX request detected, using partial template")
        return super().render_to_response(context, **response_kwargs)