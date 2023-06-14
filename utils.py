from shared import app
from sanic import Request

def get_post(request: Request):
    data = request.form
    for key in data:
        data[key] = data[key]
    return data

async def render_template(r, template, *args, **kwargs):
    text = await app.ctx.jinja.render_async(template, r, *args, **kwargs)
    return text