from django.views import View
from django.shortcuts import render

#about.html template

class AboutView(View):
    def get(self, request):
        """
        Handle GET requests for the about page.
        """
        return render(request, 'about.html')