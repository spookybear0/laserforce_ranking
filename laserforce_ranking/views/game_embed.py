from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from laserforce_ranking.models import SM5Game
from laserforce_ranking.helpers.embedhelper import generate_sm5_game_image
from django.views import View


class SM5GameEmbedImageView(View):
    def get(self, request, tdf_name,):
        sm5game = get_object_or_404(
            SM5Game.objects.prefetch_related(
                "teams__entity_starts__entity_end",
                "teams__entity_starts__sm5_stats",
            ),
            tdf_name=tdf_name
        )

        image = generate_sm5_game_image(sm5game)

        return HttpResponse(
            image.getvalue(),
            content_type="image/png",
        )