from django.templatetags.static import static
from django.urls import reverse
from jinja2 import Environment


def environment(**options):
    """Configures the Jinja2 environment with Django global functions."""
    env = Environment(**options, enable_async=True)

    # inject Django helper functions into Jinja2 templates
    env.globals.update(
        {
            "url": reverse,
            "static": static,
        }
    )

    return env