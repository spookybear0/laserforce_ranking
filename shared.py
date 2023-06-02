from mysql import MySQLPool
import jinja2
from sanic import Sanic
from sanic_jinja2 import SanicJinja2

app = Sanic("laserforce_rankings")
app.ctx.jinja = SanicJinja2(app, loader=jinja2.FileSystemLoader("./assets/html"), pkg_path="assets/html", extensions=["jinja2.ext.loopcontrols"])
app.ctx.sql = MySQLPool()