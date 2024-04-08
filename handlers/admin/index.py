from sanic import Request, response
from shared import app
from utils import render_template, admin_only
from helpers.ratinghelper import recalculate_ratings, recalculate_laserball_ratings, recalculate_sm5_ratings
from helpers.cachehelper import flush_cache
from sanic.log import logger
import asyncio

@app.get("/admin")
@admin_only
async def admin_index(request: Request) -> str:
    return await render_template(request,
        "admin/index.html",
    )

@app.post("/admin/recalculate_ratings")
@admin_only
async def admin_recalculate_ratings(request: Request) -> str:
    asyncio.create_task(recalculate_ratings(), name="Recalculate Ratings")

    return response.json({"status": "ok"})

@app.post("/admin/recalculate_sm5_ratings")
@admin_only
async def admin_recalculate_sm5_ratings(request: Request) -> str:
    asyncio.create_task(recalculate_sm5_ratings(), name="Recalculate SM5 Ratings")

    return response.json({"status": "ok"})

@app.post("/admin/recalculate_laserball_ratings")
@admin_only
async def admin_recalculate_lb_ratings(request: Request) -> str:
    asyncio.create_task(recalculate_laserball_ratings(), name="Recalculate Laserball Ratings")

    return response.json({"status": "ok"})

@app.post("/admin/flush_cache")
@admin_only
async def admin_flush_cache(request: Request) -> str:
    logger.info("Flushing cache")
    flush_cache()
    logger.info("Cache flushed")

    return response.json({"status": "ok"})