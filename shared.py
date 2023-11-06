from sanic import Sanic
from sentry_sdk.integrations.sanic import SanicIntegration
from config import config
import sentry_sdk

sentry_sdk.init(
    dsn=config["sentry_dsn"],
    integrations=[
        SanicIntegration(),
    ],

    traces_sample_rate=1.0,
    send_default_pii=True,
    environment=config["sentry_environment"]
)

app = Sanic.get_app("laserforce_rankings")