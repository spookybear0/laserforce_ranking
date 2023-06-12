from mysql import MySQLPool
import jinja2
from sanic import Sanic
from sentry_sdk.integrations.sanic import SanicIntegration
from sanic_jinja2 import SanicJinja2
from config import config
import sentry_sdk
from sanic_cors import CORS

sentry_sdk.init(
    dsn=config["sentry_dsn"],
    integrations=[
        SanicIntegration(),
    ],

    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    send_default_pii=True,
    environment=config["sentry_environment"]
)

app = Sanic("laserforce_rankings")
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.ctx.jinja = SanicJinja2(app, loader=jinja2.FileSystemLoader("./assets/html"), pkg_path="assets/html", extensions=["jinja2.ext.loopcontrols"])
app.ctx.sql = MySQLPool()
app.ctx.config = config