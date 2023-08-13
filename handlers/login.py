from sanic import Request
from shared import app
from utils import render_template

@app.get("/login")
async def login(request: Request):
    return await render_template(request, "login.html")

@app.post("/login")
async def login_post(request: Request):
    pass