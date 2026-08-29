from django.views import View
from django.views.generic import ListView
from django.shortcuts import render
from laserforce_ranking.models import Player
from django.db.models import F, Value, FloatField, ExpressionWrapper, Q

#matchmaker.html template

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

        return render(request, "matchmaker.html", context={"players": players})
    
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
        