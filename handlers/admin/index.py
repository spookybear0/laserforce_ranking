from sanic import Request, response
from shared import app
from utils import render_template, admin_only
from helpers.ratinghelper import recalculate_ratings
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