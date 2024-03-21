from sanic import Request
from sanic.log import logger

from db.game import Events
from helpers.tdfhelper import get_arguments_from_event
from shared import app
from utils import admin_only


@app.get("/admin/backfill_events")
@admin_only
async def backfill_events(request: Request) -> str:
    response = await request.respond(content_type="text/html")

    await response.send("<html><body><H1>Updating</H1>\n")

    # Get all events. We only need those without an action. If it has one, it has already been migrated.
    events = await Events.filter(action="").all()
    updated_event_count = await _update_events(events)

    await response.send(f"<h2>All done.</h2>\n{updated_event_count} events updated.\n</body></html>")

    return ""


async def _update_events(events: list[Events]) -> int:
    for event in events:
        semantic_arguments = get_arguments_from_event(event.arguments)
        event.entity1 = semantic_arguments["entity1"]
        event.entity2 = semantic_arguments["entity2"]
        event.action = semantic_arguments["action"]

    if events:
        await Events.bulk_update(events, fields=['entity1', 'action', 'entity2'])
        logger.info('Updating %d events' % len(events))

    return len(events)
