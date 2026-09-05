from django.views import View
from django.views.generic import ListView, TemplateView
from django.shortcuts import render
from laserforce_ranking.models import Player, GameType, IntRole, Role, RoleLock, EntityType
from laserforce_ranking.rating import Rating, MU, SIGMA
from laserforce_ranking.matchmake import matchmake_advanced, matchmake_teams, get_win_chances
from django.db.models import F, Value, FloatField, ExpressionWrapper, Q
from django.db.models.fields.json import KT
from django.db.models.functions import Cast
from laserforce_ranking.models import SM5Game
import json
from asgiref.sync import sync_to_async
from typing import Optional
from logging import getLogger

logger = getLogger(__name__)

class FakePlayer:
    """
    A placeholder class for unrated players.
    """
    def __init__(self, entity_id):
        self.codename = "Unrated Player"
        self.entity_id = entity_id
        self.rating = Rating(mu=MU, sigma=SIGMA).ordinal()
        logger.debug(f"Created FakePlayer with entity_id: {entity_id}")
    
    async def get_rating(self, mode: GameType, site: str, role: IntRole = None) -> Rating:
        """
        Returns a default rating for unrated players.
        """
        logger.debug(f"Getting default rating for FakePlayer with entity_id: {self.entity_id}")
        return Rating(mu=MU, sigma=SIGMA)

class MatchmakerView(View):
    http_method_names = ["get"]

    async def get(self, request, tdf_name: Optional[str] = None):
        """
        Handle GET requests for the matchmaker page.
        """
        logger.info("Handling GET request for MatchmakerView")
        players = {player.entity_id: player async for player in Player.objects.annotate(
            rating=ExpressionWrapper(
                Cast(KT(f"ratings__global__sm5__mu"), FloatField())
                - Cast(KT(f"ratings__global__sm5__sigma"), FloatField()) * Value(3.0),
                output_field=FloatField(),
            ),
        ).order_by('-rating')}

        logger.debug(f"Retrieved {len(players)} players for matchmaker view")

        if tdf_name:
            # get teams/roles from the game with the given tdf_name
            game = await SM5Game.objects.filter(tdf_name=tdf_name).afirst()
            print(f"Retrieved game for tdf_name {tdf_name}: {game}")

            new_teams = []
            new_roles = []
            teams = await game.get_teams()
            print(f"Retrieved teams from game: {teams}")

            for team in teams:
                print(f"Processing team: {team}")
                entitys = team.entity_starts.filter(type=EntityType.PLAYER).all()
                new_teams.append(
                    [
                        players[entity.entity_id] if entity.entity_id[0] == "#"
                        else FakePlayer(entity.entity_id)
                        async for entity in entitys
                    ]
                )
                new_roles.append([
                    entity.role
                    async for entity in entitys
                ])
            
            print(f"New teams: {new_teams}, New roles: {new_roles}")
        else:
            new_teams = [[], []]
            new_roles = [[], []]

        # sort by role

        for i, team in enumerate(new_teams):
            sorted_team = sorted(zip(team, new_roles[i]), key=lambda x: x[1].value)
            new_teams[i], new_roles[i] = zip(*sorted_team) if sorted_team else ([], [])

        context = {
            "players": players.values(),
            "teams": new_teams,
            "roles": new_roles,
            "locks": [["none" for _ in team] for team in new_teams],
            "win_chances": [[0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5]], # default win chances
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

        logger.info(f"Fetching players with search: '{search}', mode: '{mode}', site: '{site}'")

        players = Player.objects.annotate(
            rating=ExpressionWrapper(
                Cast(KT(f"ratings__{site}__{mode}__mu"), FloatField())
                - Cast(KT(f"ratings__{site}__{mode}__sigma"), FloatField()) * Value(3.0),
                output_field=FloatField(),
            )
        ).order_by('-rating')

        if search:
            players = players.filter(
                Q(codename__icontains=search)
            )
            logger.debug(f"Filtered players based on search: {search}")

        return players
    
class MatchmakerTeamsView(TemplateView):
    template_name = "partials/matchmaker/teams.html"
    http_method_names = ["post"]

    async def post(self, request, *args, **kwargs):
        """
        Handle POST requests for generating teams based on selected players.
        """
        logger.info("Handling POST request for MatchmakerTeamsView")
        context = self.get_context_data(**kwargs)

        teams = json.loads(self.request.POST.get("teams", "[]"))
        mode = self.request.POST.get("mode", "sm5").strip()
        site = self.request.POST.get("site", "global").strip()
        roles_enabled = self.request.POST.get("roles", "false").strip().lower() == "true"
        matchmake = request.GET.get("matchmake", "false").strip().lower() == "true"

        logger.debug(f"Received teams: {teams}, mode: {mode}, site: {site}, roles_enabled: {roles_enabled}, matchmake: {matchmake}")

        entity_ids = [player["entity_id"] for team in teams for player in team]

        players = {player.entity_id: player async for player in Player.objects.filter(entity_id__in=entity_ids).annotate(
            rating=ExpressionWrapper(
                Cast(KT(f"ratings__{site}__{mode}__mu"), FloatField())
                - Cast(KT(f"ratings__{site}__{mode}__sigma"), FloatField()) * Value(3.0),
                output_field=FloatField(),
            )
        ).order_by('-rating')}

        logger.debug(f"Fetched players for entity_ids: {entity_ids}")

        new_teams = []
        new_roles = []
        locks = []
        role_lock_dict = {}

        if teams:
            for team in teams:
                new_teams.append([
                    players[player["entity_id"]] if "unrated-" not in player["entity_id"] else FakePlayer(player["entity_id"]) for player in team
                ])
                new_roles.append([IntRole.from_role(Role(player["role"])) for player in team])
                locks.append([player.get("lock", "none") for player in team])
                role_lock_dict.update({player["entity_id"]: RoleLock(player.get("lock", "none")) for player in team})
        else:
            new_teams = [[], []]
            new_roles = [[], []]

        if matchmake:
            logger.info("Performing matchmaking")
            if roles_enabled:
                new_teams, new_roles = await matchmake_advanced(list(players.values()), 2, GameType(mode), site, role_lock_dict)
            else:
                new_teams = await matchmake_teams(list(players.values()), 2, GameType(mode), site)

        if roles_enabled:
            for i, team in enumerate(new_teams):
                sorted_team = sorted(zip(team, new_roles[i]), key=lambda x: x[1].value)
                new_teams[i], new_roles[i] = zip(*sorted_team) if sorted_team else ([], [])

        context["teams"] = new_teams
        context["roles"] = new_roles
        context["locks"] = [[role_lock_dict.get(player.entity_id, RoleLock("none")).value for player in team] for team in new_teams]
        context["roles_enabled"] = roles_enabled
        context["win_chances"] = await get_win_chances(new_teams, GameType(mode), site, roles=new_roles if roles_enabled else None) \
                if new_teams and new_teams[0] and new_teams[1] else [[0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5]]

        logger.debug("Matchmaking completed and context updated")

        return self.render_to_response(context)
    
class MatchmakerUpdateView(TemplateView):
    template_name = "partials/matchmaker/update.html"
    http_method_names = ["post"]

    async def post(self, request, *args, **kwargs):
        """
        Updates player and team tables
        """
        logger.info("Handling POST request for MatchmakerUpdateView")
        context = self.get_context_data(**kwargs)

        teams = json.loads(self.request.POST.get("teams", "[]"))
        mode = request.POST.get("mode", "sm5").strip()
        site = request.POST.get("site", "global").strip()
        roles_enabled = request.POST.get("roles", "false").strip().lower() == "true"

        logger.debug(f"Received teams: {teams}, mode: {mode}, site: {site}, roles_enabled: {roles_enabled}")

        rating_expr = ExpressionWrapper(
            Cast(KT(f"ratings__{site}__{mode}__mu"), FloatField())
            - Cast(KT(f"ratings__{site}__{mode}__sigma"), FloatField()) * Value(3.0),
            output_field=FloatField(),
        )

        entity_ids = [player["entity_id"] for team in teams for player in team]
        players = {player.entity_id: player async for player in Player.objects.filter(entity_id__in=entity_ids).annotate(rating=rating_expr)}

        logger.debug(f"Fetched players for entity_ids: {entity_ids}")

        new_teams = []
        new_roles = []
        locks = []

        if teams:
            for team in teams:
                new_teams.append([
                    players[player["entity_id"]] if "unrated-" not in player["entity_id"] else FakePlayer(player["entity_id"]) for player in team
                ])
                new_roles.append([IntRole.from_role(Role(player["role"])) for player in team])
                locks.append([player.get("lock", "none") for player in team])
        else:
            new_teams = [[], []]
            new_roles = [[], []]

        context["players"] = Player.objects.annotate(rating=rating_expr).order_by('-rating')
        context["teams"] = new_teams
        context["roles"] = new_roles
        context["locks"] = locks
        context["roles_enabled"] = roles_enabled
        context["win_chances"] = await get_win_chances(new_teams, GameType(mode), site, roles=new_roles if roles_enabled else None) \
            if new_teams and new_teams[0] and new_teams[1] else [[0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5]]

        logger.debug("Updated context with new teams and players")

        return self.render_to_response(context)