from sanic.exceptions import NotFound
from utils import render_template
from sanic import Request
from shared import app

@app.exception(NotFound)
async def index(request: Request, exception: Exception) -> str:
    return await render_template(request, "errors/404.html")