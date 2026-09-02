from django.views import View
from django.views.generic import ListView, TemplateView
from django.shortcuts import render
from laserforce_ranking.models import Player, GameType, IntRole, Role
from laserforce_ranking.rating import Rating, MU, SIGMA
from laserforce_ranking.matchmake import matchmake_advanced, matchmake_teams, get_win_chances
from django.db.models import F, Value, FloatField, ExpressionWrapper, Q
import json
from asgiref.sync import sync_to_async

class FakePlayer:
    """
    A placeholder class for unrated players.
    """
    def __init__(self, entity_id):
        self.codename = "Unrated Player"
        self.entity_id = entity_id
        self.rating = Rating(mu=MU, sigma=SIGMA).ordinal()
    
    async def get_rating(self, mode: GameType, site: str, role: IntRole = None) -> Rating:
        """
        Returns a default rating for unrated players.
        """
        return Rating(mu=MU, sigma=SIGMA)

class MatchmakerView(View):
    def get(self, request):
        """
        Handle GET requests for the matchmaker page.
        """

        players = Player.objects.annotate(
            rating=ExpressionWrapper(
                F(f"ratings__global__sm5__mu") - \
                F(f"ratings__global__sm5__sigma") * Value(3, output_field=FloatField()),
                output_field=FloatField()
            ),
        ).order_by('-rating')

        context = {
            "players": players,
            "teams": [[], []],  # Initialize with two empty teams
            "roles": [[], []],
            "win_chances": [[0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5]],  # Default win chances for two teams
            "roles_enabled": True
        }

        return render(request, "matchmaker.html", context=context)
    
class MatchmakerPlayersView(ListView):
    model = Player
    template_name = "partials/matchmaker/player_table.html"
    context_object_name = "players"

    def get_queryset(self):
        search = self.request.GET.get("search", "").strip()
        mode = self.request.GET.get("mode", "sm5").strip()
        site = self.request.GET.get("site", "global").strip()

        players = Player.objects.annotate(
            rating=ExpressionWrapper(
                F(f"ratings__{site}__{mode}__mu") - \
                F(f"ratings__{site}__{mode}__sigma") * Value(3, output_field=FloatField()),
                output_field=FloatField()
            ),
        ).order_by('-rating')

        if search:
            players = players.filter(
                Q(codename__icontains=search)
            )

        return players
    
class MatchmakerTeamsView(TemplateView):
    template_name = "partials/matchmaker/teams.html"
    http_method_names = ["post"]

    async def post(self, request, *args, **kwargs):
        """
        Handle POST requests for generating teams based on selected players.
        """
        context = self.get_context_data(**kwargs)

        teams = json.loads(self.request.POST.get("teams", "[]"))
        mode = self.request.POST.get("mode", "sm5").strip()
        site = self.request.POST.get("site", "global").strip()
        roles_enabled = self.request.POST.get("roles", "false").strip().lower() == "true"
        matchmake = request.POST.get("matchmake", "false").strip().lower() == "true"

        entity_ids = [player["entity_id"] for team in teams for player in team]

        players = {player.entity_id: player async for player in Player.objects.filter(entity_id__in=entity_ids).annotate(
            rating=ExpressionWrapper(
                F(f"ratings__{site}__{mode}__mu") - \
                F(f"ratings__{site}__{mode}__sigma") * Value(3, output_field=FloatField()),
                output_field=FloatField()
            ),
        ).order_by('-rating')}

        new_teams = []
        new_roles = []

        if teams:
            for i, team in enumerate(teams):
                new_teams.append([
                    players[player["entity_id"]] if "unrated-" not in player["entity_id"] else FakePlayer(player["entity_id"]) for player in team
                ])
                new_roles.append([IntRole.from_role(Role(player["role"])) for player in team])
        else:
            new_teams = [[], []]
            new_roles = [[], []]

        # matchmake

        if matchmake:
            if roles_enabled:
                new_teams, new_roles = await matchmake_advanced(list(players.values()), 2, GameType(mode), site)
            else:
                new_teams = await matchmake_teams(list(players.values()), 2, GameType(mode), site)

        # we need to sort the new teams by role
        # commander, heavy, scout, ammo, medic

        if roles_enabled:
            for i, team in enumerate(new_teams):
                sorted_team = sorted(zip(team, new_roles[i]), key=lambda x: x[1].value)

                new_teams[i], new_roles[i] = zip(*sorted_team) if sorted_team else ([], [])

        context["teams"] = new_teams
        context["roles"] = new_roles
        context["roles_enabled"] = roles_enabled
        context["win_chances"] = await get_win_chances(new_teams, GameType(mode), site, roles=new_roles if roles_enabled else None) \
                if new_teams and new_teams[0] and new_teams[1] else [[0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5]]
            


        return self.render_to_response(context)
    
class MatchmakerUpdateView(TemplateView):
    template_name = "partials/matchmaker/update.html"
    http_method_names = ["post"]

    async def post(self, request, *args, **kwargs):
        """
        Updates player and team tables
        """

        context = self.get_context_data(**kwargs)

        teams = json.loads(self.request.POST.get("teams", "[]"))
        mode = request.POST.get("mode", "sm5").strip()
        site = request.POST.get("site", "global").strip()
        roles_enabled = request.POST.get("roles", "false").strip().lower() == "true"

        rating_expr = ExpressionWrapper(
            F(f"ratings__{site}__{mode}__mu") - \
            F(f"ratings__{site}__{mode}__sigma") * Value(3, output_field=FloatField()),
            output_field=FloatField()
        )

        # teams
        entity_ids = [player["entity_id"] for team in teams for player in team]
        players = {player.entity_id: player async for player in Player.objects.filter(entity_id__in=entity_ids).annotate(rating=rating_expr)}

        new_teams = []
        new_roles = []

        if teams:
            for i, team in enumerate(teams):
                new_teams.append([
                    players[player["entity_id"]] if "unrated-" not in player["entity_id"] else FakePlayer(player["entity_id"]) for player in team
                ])
                new_roles.append([IntRole.from_role(Role(player["role"])) for player in team])
        else:
            new_teams = [[], []]
            new_roles = [[], []]

        context["players"] = Player.objects.annotate(rating=rating_expr).order_by('-rating')
        context["teams"] = new_teams
        context["roles"] = new_roles
        context["roles_enabled"] = roles_enabled
        context["win_chances"] = await get_win_chances(new_teams, GameType(mode), site, roles=new_roles if roles_enabled else None) \
            if new_teams and new_teams[0] and new_teams[1] else [[0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5]]

        return self.render_to_response(context)