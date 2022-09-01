from sanic import Request
from shared import app
from utils import render_template

# shows top x
@app.get("/")
async def index(request: Request):
    return await render_template(request, "index.html")
    #return await render_template(request, "top.html", players=await userhelper.get_top(GameType.SM5, 50))