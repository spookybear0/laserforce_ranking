from sanic import Request

from db.sm5 import SM5Game, SM5_LASERRANK_VERSION
from helpers.sm5helper import update_team_sizes, update_winner
from shared import app
from utils import admin_only
from sanic.log import logger

_BATCH_SIZE = 20


@app.post("/admin/migrate_games")
@admin_only
async def migrate_games(request: Request) -> str:
    response = await request.respond(content_type="text/html")

    updated_games_count = 0

    while True:
        # Get all SM5 games. We only need those that aren't already on the latest version.
        games = await SM5Game.filter(laserrank_version__not=SM5_LASERRANK_VERSION).limit(_BATCH_SIZE).all()

        # Keep going until there's nothing left to update.
        if not games:
            break

        update_count = await _migrate_games(games)
        updated_games_count += update_count

        logger.info(f"Updated {update_count} games to version {SM5_LASERRANK_VERSION}")

    return response.json({"status": "ok", "updated_games_count": updated_games_count})


async def _migrate_games(games: list[SM5Game]) -> int:
    for game in games:
        if game.laserrank_version < SM5_LASERRANK_VERSION:
            logger.info(f"Updating game {game.id} from version {game.laserrank_version} to {SM5_LASERRANK_VERSION}")
            if game.laserrank_version < 2:
                await update_winner(game)
            if game.laserrank_version < 3:
                await update_team_sizes(game)
        game.laserrank_version = SM5_LASERRANK_VERSION
        await game.save()

    return len(games)
