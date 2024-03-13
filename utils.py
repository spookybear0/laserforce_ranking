from sanic import Request, response
from db.types import Permission
from typing import Callable, Any, Union
from shared import app

def get_post(request: Request) -> dict:
    """
    DEPRECATED
    """
    data = request.form
    for key in data:
        data[key] = data[key]
    return data

async def render_template(r, template, *args, **kwargs) -> str:
    additional_kwargs = {
        "session": r.ctx.session,
        "config": r.app.ctx.config,
        "Permission": Permission
    }

    kwargs = {**kwargs, **additional_kwargs}

    text = await app.ctx.jinja.render_async(template, r, *args, **kwargs)
    return text

def admin_only(f) -> Callable:
    async def wrapper(request: Request, *args, **kwargs) -> Union[response.HTTPResponse, Any]:
        if not request.ctx.session.get("permissions", 0) == Permission.ADMIN:
            request.ctx.session["previous_page"] = request.path
            return response.redirect("/login")
        return await f(request, *args, **kwargs)
    return wrapper

def is_admin(request: Request) -> bool:
    return request.ctx.session.get("permissions", 0) == Permission.ADMIN