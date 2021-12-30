# flake8: noqa: F405
"""
Production Configurations
"""
import sentry_sdk
from dealer.auto import auto
from sentry_sdk.integrations.django import DjangoIntegration

from .common import *  # noqa

# SECRET KEY
SECRET_KEY = env.str("DJANGO_SECRET_KEY")
# END SECRET KEY

# EMAIL
DEFAULT_FROM_EMAIL = env.str(
    "DJANGO_DEFAULT_FROM_EMAIL", "poradnia <noreply@porady.siecobywatelska.pl>"
)
EMAIL_SUBJECT_PREFIX = env.str("DJANGO_EMAIL_SUBJECT_PREFIX", "[poradnia] ")

EMAIL_CONFIG = env.email_url("EMAIL_URL", default="smtp://localhost:25")
vars().update(EMAIL_CONFIG)

SERVER_EMAIL = env.str("DJANGO_SERVER_EMAIL")
# END EMAIL

# TEMPLATE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
TEMPLATES[0]["OPTIONS"]["loaders"] = (
    (
        "django.template.loaders.cached.Loader",
        (
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ),
    ),
)
# END TEMPLATE CONFIGURATION

# Your production stuff: Below this line define 3rd party libary settings
# Ustaw wartość twojego DSN
REVISION_ID = auto.revision

sentry_sdk.init(
    dsn=env.str("RAVEN_DSN", "http://example.com"),
    release=REVISION_ID,
    integrations=[DjangoIntegration()],
)

CACHES = {"default": env.cache()}

LETTER_RECEIVE_SECRET = env.str("LETTER_RECEIVE_SECRET")
