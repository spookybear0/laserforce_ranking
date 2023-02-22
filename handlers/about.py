from sanic import Request
from shared import app
from utils import render_template

@app.get("/about")
async def about(request: Request):
    return await render_template(request, "about.html")