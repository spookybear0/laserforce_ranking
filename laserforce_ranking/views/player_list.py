from django.views.generic import ListView
from django.shortcuts import render
import random

class PlayerListView(ListView):
    template_name = "player_list.html"
    context_object_name = "players"
    paginate_by = 10  # Adjust as needed

    def get_queryset(self):
        print("page", self.request.GET.get("page"))
        # Fallback to 'name' if no sort parameter is provided
        sort_by = self.request.GET.get("sort", "codename") 

        # Map allowed frontend parameters to model fields safely
        allowed_fields = {
            "codename": "codename",
            "-codename": "-codename",
            "home_site": "home_site",
            "-home_site": "-home_site",
            "rating": "rating",
            "-rating": "-rating",
            "games": "games",
            "-games": "-games",
        }

        db_field = allowed_fields.get(sort_by, "-rating")
        return ["test list", "test list2", random.randint(1, 100)] + [_ for _ in range(10)]


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass current sorting to the template to toggle direction
        context["current_sort"] = self.request.GET.get("sort", "-rating")
        context["current_page"] = self.request.GET.get("page", 1)
        context["current_mode"] = self.request.GET.get("mode", "sm5")
        print(self.request.GET)
        return context

    def render_to_response(self, context, **response_kwargs):
        # Intercept HTMX requests to return only the partial fragment
        if self.request.htmx:
            self.template_name = "partials/player_table.html"
        print(context)
        return super().render_to_response(context, **response_kwargs)