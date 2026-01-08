from typing import Callable, Any, Union

from sanic import Request, response

from db.player import Player
from db.types import Permission
from shared import app
from helpers.tooltiphelper import TOOLTIP_INFO


# listen before request
@app.middleware("request")
async def add_session_to_request(request: Request) -> None:
    if request.headers.get("Cookie") is not None:
        # check login with cookie
        player = await Player.filter(codename=request.cookies.get("codename")).first()
        if player is not None and player.check_password(request.cookies.get("password")):
            request.ctx.session.update({
                "codename": player.codename,
                "player_id": player.player_id,
                "permissions": player.permissions
            })


async def render_template(r, template, *args, **kwargs) -> str:
    additional_kwargs = {
        "session": r.ctx.session,
        "config": r.app.ctx.config,
        "Permission": Permission,
        "str": str,
        "tooltip_info": TOOLTIP_INFO,
        "is_admin": is_admin(r),
    }

    kwargs = {**kwargs, **additional_kwargs}

    text = await app.ctx.jinja.render_async(template, r, *args, **kwargs)
    return text


async def render_cached_template(r, template, *args, **kwargs) -> str:
    return r, template, args, kwargs


def admin_only(f) -> Callable:
    async def wrapper(request: Request, *args, **kwargs) -> Union[response.HTTPResponse, Any]:
        if not request.ctx.session.get("permissions", 0) == Permission.ADMIN:
            return response.redirect("/login")
        return await f(request, *args, **kwargs)

    wrapper.__name__ = f.__name__

    return wrapper


def is_admin(request: Request) -> bool:
    return request.ctx.session.get("permissions", 0) == Permission.ADMIN

def banner_type_to_color(type: str) -> str:
    return {
        "info": "#4da6ff",
        "warning": "#cfa602",
        "danger": "#ff4d4d",
    }.get(type, "#4da6ff")