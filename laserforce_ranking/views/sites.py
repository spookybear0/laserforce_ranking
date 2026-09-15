from laserforce_ranking.models import SITES, COMPETITIVE_SITES
from django.views.generic import View
from django.shortcuts import render
from django.db.models import FloatField, ExpressionWrapper, Count
from django.db.models.functions import Cast
from laserforce_ranking.models import Player, Game, SM5Game, NAME_TO_TEAM
import logging

logger = logging.getLogger(__name__)

class SiteListView(View):
    template_name = "sites.html"

    def get(self, request, *args, **kwargs):
        logger.debug("Fetching site list for SiteListView")
        site_data = []

        for site in SITES:
            logger.debug(f"Processing site: {site.name} (ID: {site.id})")

            games = Game.objects.filter(site_id=site.id)
            game_count = games.count()

            if game_count == 0:
                continue

            sm5_games = SM5Game.objects.filter(site_id=site.id)
            sm5_game_count = sm5_games.count()

            player_counts = (
                Player.objects
                .filter(entity_id__in=games.values_list("entity_ends__entity__entity_id", flat=True))
                .aggregate(total_players=Count("id"))
            )

            elimination_rate = (
                sm5_games.filter(last_team_standing__isnull=False).count() / sm5_game_count * 100
                if game_count > 0 else 0
            )

            # calculate arena balance metric
            team_wins = (
                sm5_games
                .filter(winner__isnull=False)
                .values("winner__color_name")
                .annotate(win_count=Count("winner"))
                .order_by("-win_count")
            )

            total_wins = sum(team["win_count"] for team in team_wins)

            arena_balance_teams = []

            for team in team_wins:
                win_percentage = (team["win_count"] / total_wins * 100) if total_wins > 0 else 0
                css_color = NAME_TO_TEAM[team['winner__color_name']].css_color_name
                arena_balance_teams.append({
                    "name": team["winner__color_name"],
                    "win_percentage": round(win_percentage, 2),
                    "css_color": css_color
                })

            site_data.append({
                "name": site.name,
                "id": site.id,
                "players": player_counts.get("total_players", 0),
                "games": game_count,
                "elimination_rate": round(elimination_rate, 2),
                "arena_balance_teams": arena_balance_teams
            })
    
        logger.debug(f"Site data compiled: {site_data}")

        site_data.sort(key=lambda x: x["games"], reverse=True)

        return render(request, self.template_name, {"sites": site_data})
