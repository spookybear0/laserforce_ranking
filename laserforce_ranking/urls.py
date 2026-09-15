"""
URL configuration for laserforce_ranking project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import api

# main site
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.IndexView.as_view(), name="index"),
    path("players", views.PlayerListView.as_view(), name="players"),
    path("games", views.GameListView.as_view(), name="games"),
    path("players/<str:entity_id>", views.PlayerView.as_view(), name="player_detail"),
    path("about", views.AboutView.as_view(), name="about"),
    path("games/<str:tdf_name>", views.GameView.as_view(), name="game_detail"),
    path("games/<str:tdf_name>/embed.png", views.SM5GameEmbedImageView.as_view(), name="game_embed"),
    path("team_builder", views.TeamBuilderView.as_view(), name="team_builder"),
    path("team_builder/players", views.TeamBuilderPlayersView.as_view(), name="team_builder_players"),
    path("team_builder/teams", views.TeamBuilderTeamsView.as_view(), name="team_builder_teams"),
    path("team_builder/update", views.TeamBuilderUpdateView.as_view(), name="team_builder_update"),
    path("team_builder/<str:tdf_name>", views.TeamBuilderView.as_view(), name="team_builder_rematchmake"),
    path("sites/", views.SiteListView.as_view(), name="sites"),
    path("util/upload_tdf", views.UploadTDFView.as_view(), name="upload_tdf"),
]

# /api
urlpatterns += [
    path("api/tdf/<str:tdf_name>", api.get_tdf, name="api_get_tdf"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)