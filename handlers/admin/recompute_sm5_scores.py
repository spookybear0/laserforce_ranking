from sanic import Request

from db.sm5 import SM5Game, SM5_LASERRANK_VERSION
from helpers.sm5helper import update_winner
from shared import app
from utils import admin_only

_BATCH_SIZE = 20


@app.get("/admin/recompute_sm5_scores")
@admin_only
async def recompute_sm5_scores(request: Request) -> str:
    response = await request.respond(content_type="text/html")

    await response.send("<html><body><H1>Updating...</H1>\n")

    updated_games_count = 0

    while True:
        # Get all SM5 games. We only need those that aren't already on the latest version.
        games = await SM5Game.filter(laserrank_version__not=SM5_LASERRANK_VERSION).limit(_BATCH_SIZE).all()

        # Keep going until there's nothing left to update.
        if not games:
            break

        update_count = await _update_games(games)
        updated_games_count += update_count
        await response.send(f"Updated {update_count} games\n<br>")

    await response.send(f"<h2>All done.</h2>\n{updated_games_count} games updated.\n</body></html>")

    return ""


async def _update_games(games: list[SM5Game]) -> int:
    for game in games:
        if game.laserrank_version < 2:
            await update_winner(game)
        game.laserrank_version = SM5_LASERRANK_VERSION
        await game.save()

    return len(games)
