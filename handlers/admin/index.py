import asyncio

from sanic import Request, response
from sanic.log import logger

from helpers.cachehelper import flush_cache
from helpers.ratinghelper import recalculate_ratings, recalculate_laserball_ratings, recalculate_sm5_ratings
from shared import app
from utils import render_template, admin_only

def reset_banner() -> None:
    app.ctx.banner = {
        "text": None,
        "type": None,
    }
    

@app.get("/admin")
@admin_only
async def admin_index(request: Request) -> str:
    return await render_template(request,
                                 "admin/index.html",
                                 )


@app.post("/admin/recalculate_ratings")
@admin_only
async def admin_recalculate_ratings(request: Request) -> str:
    request.app.ctx.banner["text"] = "Rating recalculation in progress, stats may be inaccurate"
    asyncio.create_task(recalculate_ratings(), name="Recalculate Ratings").add_done_callback(lambda _: reset_banner())

    return response.json({"status": "ok"})


@app.post("/admin/recalculate_sm5_ratings")
@admin_only
async def admin_recalculate_sm5_ratings(request: Request) -> str:
    request.app.ctx.banner["text"] = "Rating recalculation in progress, stats may be inaccurate"
    asyncio.create_task(recalculate_sm5_ratings(), name="Recalculate SM5 Ratings").add_done_callback(lambda _: reset_banner())

    return response.json({"status": "ok"})


@app.post("/admin/recalculate_laserball_ratings")
@admin_only
async def admin_recalculate_lb_ratings(request: Request) -> str:
    request.app.ctx.banner["text"] = "Rating recalculation in progress, stats may be inaccurate"
    asyncio.create_task(recalculate_laserball_ratings(), name="Recalculate Laserball Ratings").add_done_callback(lambda _: reset_banner())

    return response.json({"status": "ok"})


@app.post("/admin/flush_cache")
@admin_only
async def admin_flush_cache(request: Request) -> str:
    logger.info("Flushing cache")
    flush_cache()
    logger.info("Cache flushed")

    return response.json({"status": "ok"})

@app.post("/admin/set_banner")
@admin_only
async def admin_set_banner(request: Request) -> str:
    request.app.ctx.banner["text"] = request.json.get("text") or None
    request.app.ctx.banner["type"] = request.json.get("type") or None

    flush_cache()

    return response.json({"status": "ok"})