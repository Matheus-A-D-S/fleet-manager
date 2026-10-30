import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse


def live(request):
    """Liveness: o processo está de pé."""
    return JsonResponse({"status": "ok"})


def ready(request):
    """Readiness: dependências (PostgreSQL e Redis) respondendo."""
    checks = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
    try:
        redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=1).ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
    healthy = all(v == "ok" for v in checks.values())
    return JsonResponse({"status": "ok" if healthy else "degraded", "checks": checks}, status=200 if healthy else 503)
