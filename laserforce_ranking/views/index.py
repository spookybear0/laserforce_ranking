from django.views import View
from django.shortcuts import render

#index.html template

class IndexView(View):
    def get(self, request):
        """
        Handle GET requests for the index page.
        """
        return render(request, 'index.html')