from sanic import Sanic
from sentry_sdk.integrations.sanic import SanicIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from config import config
import sentry_sdk
import logging

sentry_sdk.init(
    dsn=config["sentry_dsn"],
    integrations=[
        SanicIntegration(),
        LoggingIntegration(
            level=logging.DEBUG,
            event_level=logging.WARNING
        ),
    ],
    traces_sample_rate=1.0,
    send_default_pii=True,
    environment=config["sentry_environment"],
    enable_tracing=True,
)

app = Sanic.get_app("laserforce_rankings")