from django.views import View
from django.views.generic.detail import DetailView
from django.shortcuts import render
from laserforce_ranking.models import Game, Player
from laserforce_ranking.matchmake import get_win_chance
from asgiref.sync import sync_to_async

class GameView(DetailView):
    model = Game
    template_name = "game.html"
    context_object_name = "game"
    http_method_names = ["get"]

    def get_object(self, queryset=None):
        """
        Override get_object to fetch the player based on the provided ID.
        """
        tdf_name = self.kwargs.get("tdf_name")
        return Game.objects.get(tdf_name=tdf_name)
    
    async def sm5(self, game: Game, context):
        context["rematchmake_obj"] = {}
        context["teams"] = [team async for team in game.teams.order_by("-score")][:2]
        context["get_codename"] = lambda entity: Player.objects.get(entity_id=entity.entity_id).codename
        context["win_chances"] = await game.get_win_chance_before_game(consider_site=False, consider_roles=False)

    async def laserball(self, game, context):
        pass
    
    async def get(self, request, *args, **kwargs):
        """
        Handle GET requests for the game detail page.
        """
        self.object = await sync_to_async(self.get_object)()
        context = self.get_context_data(object=self.object)
        game = self.object

        if sync_to_async(hasattr)(game, "sm5game"):
            game = await sync_to_async(getattr)(game, "sm5game")
            await self.sm5(game, context)
        elif sync_to_async(hasattr)(game, "laserballgame"):
            game = await sync_to_async(getattr)(game, "laserballgame")
            await self.laserball(game, context)
            
        self.object = game
        context.update({
            "object": self.object,
            "game": self.object,
        })

        return self.render_to_response(context)