import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class _RedisUp:
    def ping(self):
        return True


def test_liveness(api):
    response = api.get("/api/health/")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    assert response["X-Request-ID"]  # todo response carrega um id de correlação


def test_request_id_is_propagated(api):
    assert api.get("/api/health/", HTTP_X_REQUEST_ID="abc123")["X-Request-ID"] == "abc123"


def test_readiness_ok(api, monkeypatch):
    monkeypatch.setattr("apps.core.views.redis.Redis.from_url", lambda *a, **k: _RedisUp())
    response = api.get("/api/health/ready/")
    assert response.status_code == 200
    assert response.json()["checks"] == {"database": "ok", "redis": "ok"}


def test_readiness_degraded_when_redis_is_down(api, monkeypatch):
    def down(*a, **k):
        raise ConnectionError

    monkeypatch.setattr("apps.core.views.redis.Redis.from_url", down)
    response = api.get("/api/health/ready/")
    assert response.status_code == 503 and response.json()["checks"]["redis"] == "error"
