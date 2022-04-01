from global_objs import routes
from aiohttp import web
from helpers import init_sql, fetch_player_by_name, get_player


@routes.get("/api/player")
async def player(r: web.Request):
    await init_sql()

    args = r.rel_url.query

    player_id = args.get("id")
    codename = args.get("codename")

    if player_id:
        player = await get_player(player_id)
    elif codename:
        player = await fetch_player_by_name(codename)
    else:
        return web.HTTPBadRequest()

    return web.json_response(player.to_dict())
