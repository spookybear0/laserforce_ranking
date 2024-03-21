import time

from sanic import Request
from sanic.log import logger

from db.game import Events
from db.laserball import LaserballGame
from db.sm5 import SM5Game
from helpers.tdfhelper import get_arguments_from_event
from shared import app
from utils import admin_only


@app.get("/admin/backfill_events")
@admin_only
async def backfill_events(request: Request) -> str:
    response = await request.respond(content_type="text/html")

    await response.send("<html><body><H1>Updating</H1>\n")

    # Convert every game one by one.
    sm5games = await SM5Game.all()

    await _update_all_games(response, sm5games,
                            "SM5",
                            lambda game: game.start_time,
                            lambda game: game.id,
                            lambda game: game.events.all()
                            )

    lb_games = await LaserballGame.all()

    await _update_all_games(response, lb_games,
                            "Laserball",
                            lambda game: game.start_time,
                            lambda game: game.id,
                            lambda game: game.events.all()
                            )

    await response.send("<h2>All done.</h2>\n</body></html>")

    return ""


async def _update_all_games(response, games, game_type: str, time_fetcher, id_fetcher, events_fetcher):
    count = 0
    total = len(games)

    for game in games:
        log_string = f"({count}/{total}) Updating {game_type} game {time_fetcher(game).strftime('%A, %B %d at %I:%M %p')} with ID {id_fetcher(game)}"
        await response.send(f"{log_string}<br>\n")

        update_start = time.perf_counter()
        await _update_events(await events_fetcher(game))
        update_time = time.perf_counter() - update_start
        logger.info(f"{log_string} - done in {update_time * 1000}ms)")

        count += 1


async def _update_events(events: list[Events]):
    events_to_update = []
    for event in events:
        # If this event already has an action, then it has previously been
        # converted to the new format already, so we don't need to do anything
        # here.
        if event.action:
            continue

        semantic_arguments = get_arguments_from_event(event.arguments)
        event.entity1 = semantic_arguments["entity1"]
        event.entity2 = semantic_arguments["entity2"]
        event.action = semantic_arguments["action"]
        events_to_update.append(event)

    if events_to_update:
        await Events.bulk_update(events_to_update, fields=['entity1', 'action', 'entity2'])
        logger.info('Updating %d events' % len(events_to_update))
