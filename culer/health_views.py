import logging
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Lightweight production health check endpoint.
    Executes a fast database query and cache ping.
    Returns HTTP 200 JSON on healthy state, or HTTP 503 if database/cache is unreachable.
    """
    status_data = {
        "status": "ok",
        "database": "disconnected",
        "cache": "disconnected",
    }
    healthy = True

    # 1. Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        status_data["database"] = "connected"
    except Exception as exc:
        logger.error(f"Health check database failure: {exc}")
        status_data["database"] = f"error: {str(exc)}"
        healthy = False

    # 2. Cache check
    try:
        cache.set("healthz_ping", "pong", timeout=10)
        cached_val = cache.get("healthz_ping")
        if cached_val == "pong":
            status_data["cache"] = "connected"
        else:
            status_data["cache"] = "unresponsive"
            healthy = False
    except Exception as exc:
        logger.error(f"Health check cache failure: {exc}")
        status_data["cache"] = f"error: {str(exc)}"
        healthy = False

    status_code = 200 if healthy else 503
    if not healthy:
        status_data["status"] = "degraded"

    return JsonResponse(status_data, status=status_code)

