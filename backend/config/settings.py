"""
CollabSpace settings.

All secrets and environment-specific values are read from environment
variables (or a local .env file that is never committed to Git).
"""
from pathlib import Path

import environ

from .channel_layers import channel_layers

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    FRONTEND_ORIGIN=(str, "http://localhost:5173"),
    # Production (HTTPS): send cookies only over HTTPS.
    DJANGO_SECURE_COOKIES=(bool, False),
    # Set when Django runs behind a proxy that terminates HTTPS (nginx, a PaaS).
    DJANGO_BEHIND_HTTPS_PROXY=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env("DJANGO_DEBUG")
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    # daphne must come first so `runserver` serves ASGI (HTTP + WebSocket).
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "drf_spectacular",
    "channels",
    # Local apps
    "core",
    "accounts",
    "documents",
    "collaboration",
]

# Custom user model (email login). Must be set before the first migration.
AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Production only: WhiteNoise serves the admin's CSS/JS from STATIC_ROOT
# (filled by `collectstatic` in the Docker image). In development `runserver`
# serves them itself, and STATIC_ROOT does not exist.
if not DEBUG:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database: SQLite by default, PostgreSQL via DATABASE_URL.
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}

# Channel layer: how consumers talk to each other ("tell everyone in this
# document..."). In-memory works inside ONE process; with REDIS_URL set,
# Redis carries the messages, so REST views and WebSockets running in
# different processes can still reach each other.
# NOTE: the live Yjs rooms themselves stay in the memory of one process
# (see collaboration/rooms.py and docs/DEPLOYMENT.md).
REDIS_URL = env("REDIS_URL", default="")
CHANNEL_LAYERS = channel_layers(REDIS_URL)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ar"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# The React dev server proxies /api and /ws to Django, so the browser sees a
# single origin. We still trust the frontend origin explicitly for CSRF.
# Several origins can be given, separated by commas.
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[env("FRONTEND_ORIGIN")])

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Brute-force protection for the auth endpoints.
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/min",
        "register": "20/hour",
        "share": "60/hour",
        "password": "10/hour",
    },
}

# Session & CSRF cookies.
SESSION_COOKIE_HTTPONLY = True  # JavaScript can never read the session id.
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 2 weeks
CSRF_COOKIE_HTTPONLY = False  # React must read it to send the X-CSRFToken header.
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env("DJANGO_SECURE_COOKIES")
CSRF_COOKIE_SECURE = env("DJANGO_SECURE_COOKIES")
if env("DJANGO_BEHIND_HTTPS_PROXY"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Interactive API documentation: /api/docs/ (Swagger UI), /api/schema/ (OpenAPI).
SPECTACULAR_SETTINGS = {
    "TITLE": "CollabSpace API",
    "DESCRIPTION": (
        "REST API of CollabSpace, a real-time collaborative document editor.\n\n"
        "Authentication uses Django sessions: log in with `POST /api/auth/login/`, "
        "then send the `X-CSRFToken` header (value of the `csrftoken` cookie) on "
        "every write request. Real-time editing happens over the WebSocket "
        "`/ws/documents/<uuid>/` (Yjs protocol), which is not part of this schema."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/",
}

if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append(
        "rest_framework.renderers.BrowsableAPIRenderer"
    )

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "collaboration": {"handlers": ["console"], "level": "INFO"},
        "django.request": {"handlers": ["console"], "level": "ERROR"},
    },
}
