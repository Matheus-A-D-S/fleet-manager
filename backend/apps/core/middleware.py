import logging
import time
import uuid

from .logging import request_id_var

logger = logging.getLogger("app.request")


def request_id_middleware(get_response):
    """Gera/propaga X-Request-ID e registra uma linha de log por requisição."""

    def middleware(request):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_var.set(rid)
        start = time.monotonic()
        try:
            response = get_response(request)
            response["X-Request-ID"] = rid
            logger.info("%s %s %s %.0fms", request.method, request.path, response.status_code, (time.monotonic() - start) * 1000)
            return response
        finally:
            request_id_var.reset(token)

    return middleware
