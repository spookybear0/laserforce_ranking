from django.views import View
from django.shortcuts import render

#player.html template

class PlayerView(View):
    def get(self, request, pk):
        """
        Handle GET requests for the player page.
        """
        print(pk)
        return render(request, 'player.html')