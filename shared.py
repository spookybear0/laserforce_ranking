import logging

import sentry_sdk
from sanic import Sanic
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sanic import SanicIntegration
from sanic.log import logger

from config import config

if config["sentry_dsn"] is not None and config["sentry_dsn"] != "" \
    and config["sentry_environment"] is not None and config["sentry_environment"] != "":
    sentry_sdk.init(
        dsn=config["sentry_dsn"],
        integrations=[
            SanicIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR
            )
        ],
        traces_sample_rate=1.0,
        send_default_pii=True,
        environment=config["sentry_environment"],
        enable_tracing=True,
    )
else:
    logger.info("Sentry DSN or environment not set, Sentry will not be initialized.")

app = Sanic.get_app("laserforce_rankings")
