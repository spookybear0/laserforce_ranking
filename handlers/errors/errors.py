from sanic.exceptions import NotFound, ServerError
from utils import render_template
from sanic import Request
from shared import app

@app.exception(NotFound)
async def notfound(request: Request, exception: Exception) -> str:
    return await render_template(request, "errors/404.html")

@app.exception(ServerError)
async def servererror(request: Request, exception: Exception) -> str:
    return await render_template(request, "errors/500.html")