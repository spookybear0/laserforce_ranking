from shared import jinja
from sanic import Request

def get_post(request: Request):
    data = request.form
    for key in data:
        data[key] = data[key][0]
    return data

async def render_template(r, template, *args, **kwargs):
    text = jinja.render(template, r, *args, **kwargs)
    return text