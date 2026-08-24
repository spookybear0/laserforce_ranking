from django.views.generic import ListView
from django.shortcuts import render
import random

sites = ["Center 1", "Center 2", "Center 3", "Center 4", "Center 5"]

class GameListView(ListView):
    template_name = "game_list.html"
    context_object_name = "games"
    paginate_by = 10  # Adjust as needed

    def get_queryset(self):
        # Fallback to 'name' if no sort parameter is provided
        sort_by = self.request.GET.get("sort", "game") 

        # Map allowed frontend parameters to model fields safely
        allowed_fields = {
            "game": "game",
            "-game": "-game",
            "site": "site",
            "-site": "-site",
            "start_date": "start_date",
            "-start_date": "-start_date",
            "length": "length",
            "-length": "-length",
            "outcome": "outcome",
            "-outcome": "-outcome",
            "score": "score",
            "-score": "-score",
        }

        db_field = allowed_fields.get(sort_by, "game")
        return ["test list", "test list2", random.randint(1, 100)]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass current sorting to the template to toggle direction
        context["current_sort"] = self.request.GET.get("sort", "game")
        context["sites"] = sites
        context["current_page"] = self.request.GET.get("page", 1)
        context["current_site"] = self.request.GET.get("site")
        context["current_mode"] = self.request.GET.get("mode", "sm5")
        print(self.request.GET)
        return context

    def render_to_response(self, context, **response_kwargs):
        # Intercept HTMX requests to return only the partial fragment
        if self.request.htmx:
            self.template_name = "partials/game_table.html"
        print(context)
        return super().render_to_response(context, **response_kwargs)