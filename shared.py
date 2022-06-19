from mysql import MySQLPool
from aiohttp import web
import aiohttp_jinja2
import jinja2

app = web.Application()
routes = web.RouteTableDef()
templates = aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader("assets/html"))
sql = MySQLPool()