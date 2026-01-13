from typing import Callable, Any, Union

from sanic import Request, response
from sanic.log import logger

from db.player import Player
from db.types import Permission
from db.sm5 import SM5Game
from db.laserball import LaserballGame
from shared import app
from helpers.tooltiphelper import TOOLTIP_INFO
from pytailwind import Tailwind
from pathlib import Path
from tortoise.expressions import Q

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


def generate_tailwind_css() -> None:
    """
    Generates Tailwind CSS classes based on the provided configuration.
    """

    logger.info("Generating Tailwind CSS...")

    tailwind = Tailwind()


    # go through every html file and combine all content
    html_files = Path("assets/html").rglob("*.html")
    combined_content = ""
    for html_file in html_files:
        with open(html_file, 'r', encoding='utf-8') as file:
            combined_content += file.read() + "\n"
    
    # generate tailwind css classes

    tailwind_css = tailwind.generate(combined_content)

    # write the tailwind css to a file
    output_path = Path("assets/css/tailwind.css")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(tailwind_css)

    logger.info("Tailwind CSS generated successfully at 'assets/css/tailwind.css'.")

async def generate_sitemap(site_url: str) -> None:
    """
    Generates a sitemap.xml file based on the provided URLs.

    Args:
        site_url (str): The base URL of the site (e.g., "https://example.com/" or "https://example.com").
    """

    if site_url.endswith("/"):
        site_url = site_url[:-1]

    logger.info("Generating sitemap.xml...")

    # we aren't including any dynamic, admin, api, or docs pages
    # except for player pages

    # pages with no params
    urls = [
        {
            "loc": site_url + "/about",
            "changefreq": "yearly",
            "priority": "0.3"
        },
        {
            "loc": site_url + "/games",
            "changefreq": "weekly",
            "priority": "0.7"
        },
        {
            "loc": site_url + "/",
            "changefreq": "monthly",
            "priority": "1.0"
        },
        {
            "loc": site_url + "/login",
            "changefreq": "yearly",
            "priority": "0.1"
        },
        {
            "loc": site_url + "/logout",
            "changefreq": "yearly",
            "priority": "0.1"
        },
        {
            "loc": site_url + "/matchmaking",
            "changefreq": "monthly",
            "priority": "0.6"
        },
        {
            "loc": site_url + "/players",
            "changefreq": "weekly",
            "priority": "0.7"
        },
        {
            "loc": site_url + "/stats",
            "changefreq": "weekly",
            "priority": "0.8"
        }
    ]

    # add player pages
    # (only ones with a player-id, since if they don't have one in the db, they haven't played since we started tracking)
    # and we use the player-id in the url instead of the codename so that if they change their codename, the link still works

    players = await Player.filter(~Q(player_id=""), player_id__isnull=False).all()
    for player in players:
        urls.append({
            "loc": f"{site_url}/player/{player.player_id}",
            "loc_comment": player.codename,
            "changefreq": "monthly",
            "priority": "0.5",
        })

    # generate sitemap.xml content

    sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    for url in urls:
        loc_comment = url.get("loc_comment")

        sitemap_content += '  <url>\n'
        sitemap_content += f'    <loc>{url["loc"]}</loc>{f" <!--{loc_comment}-->" if loc_comment else ""}\n'
        sitemap_content += f'    <changefreq>{url["changefreq"]}</changefreq>\n'
        sitemap_content += f'    <priority>{url["priority"]}</priority>\n'
        sitemap_content += '  </url>\n'

    sitemap_content += '</urlset>'

    output_path = Path("assets/sitemap.xml")
    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(sitemap_content)

    logger.info("sitemap.xml generated successfully at 'assets/sitemap.xml'.")