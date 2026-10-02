from .base import *  # noqa: F401,F403

DEBUG = True
SECRET_KEY = SECRET_KEY or "dev-only-insecure-key-change-me"  # noqa: F405
SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY  # noqa: F405
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"