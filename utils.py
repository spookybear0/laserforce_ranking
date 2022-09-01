from shared import jinja

async def render_template(r, template, *args, **kwargs):
    text = jinja.render(template, r, *args, **kwargs)
    return text