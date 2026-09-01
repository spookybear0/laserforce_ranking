from django.contrib import admin
from .models import Team, EntityStart, Event, PlayerState, Score, EntityEnd, Game, LaserballStats, Player, SM5Stats, SM5Game

admin.site.register(Team)
admin.site.register(EntityStart)
admin.site.register(Event)
admin.site.register(PlayerState)
admin.site.register(Score)
admin.site.register(EntityEnd)
admin.site.register(Game)
admin.site.register(LaserballStats)
admin.site.register(Player)
admin.site.register(SM5Stats)
admin.site.register(SM5Game)