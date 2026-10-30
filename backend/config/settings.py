import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env(key, default=None):
    return os.environ.get(key, default)


DEV_SECRET_KEY = "dev-insecure-change-me"
SECRET_KEY = env("DJANGO_SECRET_KEY", DEV_SECRET_KEY)
DEBUG = env("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()]

INSTALLED_APPS = [
    "daphne",  # antes do staticfiles: faz o runserver atender HTTP + WebSocket
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "apps.accounts",
    "apps.fleet",
    "apps.logistics",
    "apps.alerts",
    "apps.audit",
]

MIDDLEWARE = [
    "apps.core.middleware.request_id_middleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "fleet"),
        "USER": env("POSTGRES_USER", "fleet"),
        "PASSWORD": env("POSTGRES_PASSWORD", "fleet"),
        "HOST": env("POSTGRES_HOST", "localhost"),
        "PORT": env("POSTGRES_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = env("DJANGO_STATIC_URL", "static/")
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------- DRF / JWT ----------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "config.pagination.StandardPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "config.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

SPECTACULAR_SETTINGS = {"TITLE": "FleetTrack API", "VERSION": "1.0.0"}

# ---------- CORS / Frontend ----------
FRONTEND_URL = env("FRONTEND_URL", "http://localhost:5173")
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS", FRONTEND_URL).split(",")
CSRF_TRUSTED_ORIGINS = [o for o in env("CSRF_TRUSTED_ORIGINS", "").split(",") if o]

# ---------- E-mail ----------
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = int(env("EMAIL_PORT", "1025"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env("EMAIL_USE_TLS", "0") == "1"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "FleetTrack <no-reply@fleettrack.local>")

# ---------- Celery (mensageria assíncrona) ----------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = env("CELERY_EAGER", "0") == "1"  # 1 = sem Redis (tarefas rodam na hora)
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "varredura-de-alertas": {
        "task": "apps.alerts.tasks.scan_fleet_task",
        "schedule": 3600.0,  # a cada hora
    }
}

# ---------- Channels (tempo real via WebSocket) ----------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [env("CHANNEL_REDIS_URL", "redis://localhost:6379/1")]},
    }
}

# ---------- Regras de alerta ----------
SPEED_LIMIT_KMH = int(env("SPEED_LIMIT_KMH", "90"))
ALERT_DAYS_BEFORE_EXPIRY = int(env("ALERT_DAYS_BEFORE_EXPIRY", "30"))
ALERT_KM_BEFORE_MAINTENANCE = int(env("ALERT_KM_BEFORE_MAINTENANCE", "500"))

# ---------- Logs estruturados ----------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_id": {"()": "apps.core.logging.RequestIdFilter"}},
    "formatters": {
        "json": {"()": "apps.core.logging.JsonFormatter"},
        "plain": {"format": "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["request_id"],
            "formatter": "plain" if DEBUG else "json",
        }
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}

# ---------- Segurança em produção ----------
if not DEBUG:
    if SECRET_KEY == DEV_SECRET_KEY:
        raise ImproperlyConfigured("Defina DJANGO_SECRET_KEY em produção.")
    ALLOWED_HOSTS += ["localhost", "127.0.0.1"]  # health checks internos
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_REDIRECT_EXEMPT = [r"^api/health/"]
    if env("DJANGO_HTTPS", "0") == "1":
        SECURE_SSL_REDIRECT = True
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True
        SECURE_HSTS_SECONDS = 31536000
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# ---------- Monitoramento de erros (opcional) ----------
SENTRY_DSN = env("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=env("SENTRY_ENV", "production"),
        traces_sample_rate=float(env("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        send_default_pii=False,
    )
