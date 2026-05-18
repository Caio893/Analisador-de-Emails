import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def env_bool(name: str, default: bool = False) -> bool:
    value = env(name, str(default))
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    value = env(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


DEBUG = env_bool("DEBUG", True)
SECRET_KEY = env("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-dev-only-change-me"
    else:
        raise ImproperlyConfigured("SECRET_KEY must be configured when DEBUG=false.")

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,0.0.0.0,backend" if DEBUG else "",
)
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be configured when DEBUG=false.")

BETA_BASIC_AUTH_ENABLED = env_bool("BETA_BASIC_AUTH_ENABLED", False)
BETA_BASIC_AUTH_USERNAME = env("BETA_BASIC_AUTH_USERNAME")
BETA_BASIC_AUTH_PASSWORD = env("BETA_BASIC_AUTH_PASSWORD")
BETA_BASIC_AUTH_REALM = env("BETA_BASIC_AUTH_REALM", "Email Radar Closed Beta")
BETA_BASIC_AUTH_EXEMPT_PATHS = env_list("BETA_BASIC_AUTH_EXEMPT_PATHS", "/api/healthz/")
if BETA_BASIC_AUTH_ENABLED and (not BETA_BASIC_AUTH_USERNAME or not BETA_BASIC_AUTH_PASSWORD):
    raise ImproperlyConfigured(
        "BETA_BASIC_AUTH_USERNAME and BETA_BASIC_AUTH_PASSWORD must be configured when beta auth is enabled."
    )

FRONTEND_URL = env("FRONTEND_URL", "http://localhost:8080")
BACKEND_URL = env("BACKEND_URL", "http://localhost:8000")
GOOGLE_OAUTH_REDIRECT_URI = env(
    "GOOGLE_OAUTH_REDIRECT_URI",
    f"{BACKEND_URL.rstrip('/')}/api/auth/google/callback/",
)
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET")
GOOGLE_TOKEN_ENCRYPTION_KEY = env("GOOGLE_TOKEN_ENCRYPTION_KEY")
GOOGLE_TOKEN_ENCRYPTION_FALLBACK_KEYS = env_list("GOOGLE_TOKEN_ENCRYPTION_FALLBACK_KEYS")
if not DEBUG and not GOOGLE_TOKEN_ENCRYPTION_KEY:
    raise ImproperlyConfigured("GOOGLE_TOKEN_ENCRYPTION_KEY must be configured when DEBUG=false.")
OAUTHLIB_INSECURE_TRANSPORT = env_bool("OAUTHLIB_INSECURE_TRANSPORT", DEBUG)
GMAIL_SYNC_MAX_RESULTS = int(env("GMAIL_SYNC_MAX_RESULTS", "25"))
GMAIL_BODY_CHAR_LIMIT = int(env("GMAIL_BODY_CHAR_LIMIT", "0" if DEBUG else "6000"))
ALLOW_ACCOUNT_HEADER_AUTH = env_bool("ALLOW_ACCOUNT_HEADER_AUTH", DEBUG)

OPENAI_API_KEY = env("OPENAI_API_KEY")
OPENAI_MODEL = env("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_BULK_MODEL = env("OPENAI_BULK_MODEL", OPENAI_MODEL)
OPENAI_ANALYSIS_ENABLED = env_bool("OPENAI_ANALYSIS_ENABLED", True)
OPENAI_TIMEOUT_SECONDS = float(env("OPENAI_TIMEOUT_SECONDS", "30"))
OPENAI_RETRY_ATTEMPTS = int(env("OPENAI_RETRY_ATTEMPTS", "2"))
OPENAI_RETRY_BASE_SECONDS = float(env("OPENAI_RETRY_BASE_SECONDS", "1"))
OPENAI_DAILY_ANALYSIS_LIMIT = int(env("OPENAI_DAILY_ANALYSIS_LIMIT", "0"))

REDIS_URL = env("REDIS_URL", f"redis://{env('REDIS_HOST', 'redis')}:{env('REDIS_PORT', '6379')}/0")
ANALYSIS_QUEUE_ENABLED = env_bool("ANALYSIS_QUEUE_ENABLED", False)
ANALYSIS_QUEUE_NAME = env("ANALYSIS_QUEUE_NAME", "mailguard:analysis")
ANALYSIS_QUEUE_DEDUP_KEY = env("ANALYSIS_QUEUE_DEDUP_KEY", "mailguard:analysis:queued")
ANALYSIS_QUEUE_POP_TIMEOUT = int(env("ANALYSIS_QUEUE_POP_TIMEOUT", "5"))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "api.apps.ApiConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "api.middleware.BetaBasicAuthMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

DATABASE_ENGINE = env("DATABASE_ENGINE", "postgres").lower()
POSTGRES_PASSWORD = env("POSTGRES_PASSWORD", "postgres" if DEBUG else "")
if DATABASE_ENGINE != "sqlite" and not DEBUG and not POSTGRES_PASSWORD:
    raise ImproperlyConfigured("POSTGRES_PASSWORD must be configured when DEBUG=false.")

if DATABASE_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", "mailguard"),
            "USER": env("POSTGRES_USER", "postgres"),
            "PASSWORD": POSTGRES_PASSWORD,
            "HOST": env("POSTGRES_HOST", "postgres"),
            "PORT": env("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": int(env("POSTGRES_CONN_MAX_AGE", "60")),
        }
    }

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", FRONTEND_URL)
CORS_ALLOW_CREDENTIALS = env_bool("CORS_ALLOW_CREDENTIALS", BETA_BASIC_AUTH_ENABLED)
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-mailguard-account",
    "x-requested-with",
]
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", FRONTEND_URL)
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = env("SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin")
SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "0" if DEBUG else "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", not DEBUG)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
X_FRAME_OPTIONS = "DENY"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PAGINATION_CLASS": None,
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
