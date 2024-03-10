from sanic.exceptions import NotFound, ServerError, BadRequest
from utils import render_template
from sanic import Request
from shared import app

@app.exception(NotFound)
async def notfound(request: Request, exception: Exception) -> str:
    description = exception.args[0] if exception.args else "The page you are looking for does not exist."

    return await render_template(request, "errors/404.html", description=description)

@app.exception(ServerError)
async def servererror(request: Request, exception: Exception) -> str:
    description = exception.args[0] if exception.args else "The server encountered an internal error and was unable to complete your request."

    return await render_template(request, "errors/500.html", description=description)

@app.exception(BadRequest)
async def badrequest(request: Request, exception: Exception) -> str:
    print(exception)
    description = exception.args[0] if exception.args else "The server could not understand your request."

    return await render_template(request, "errors/400.html", description=description)