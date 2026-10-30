import pytest

from apps.logistics.models import LocationPing

pytestmark = pytest.mark.django_db(transaction=True)


def ping(vehicle, **override):
    return {"vehicle": vehicle.id, "latitude": -8.76, "longitude": -63.9, "speed_kmh": 60, **override}


def test_driver_reports_position_for_own_active_trip(driver_client, active_trip, vehicle):
    response = driver_client.post("/api/logistics/pings/", ping(vehicle), format="json")
    assert response.status_code == 201
    assert LocationPing.objects.get().trip == active_trip  # vínculo definido pelo servidor


def test_driver_cannot_report_for_vehicle_without_active_trip(driver_client, vehicle):
    assert driver_client.post("/api/logistics/pings/", ping(vehicle), format="json").status_code == 403


def test_ping_validation(manager_client, vehicle):
    assert manager_client.post("/api/logistics/pings/", ping(vehicle, latitude=123), format="json").status_code == 400
    assert manager_client.post("/api/logistics/pings/", ping(vehicle, longitude=-500), format="json").status_code == 400
    assert manager_client.post("/api/logistics/pings/", ping(vehicle, speed_kmh=999), format="json").status_code == 400


def test_trip_must_belong_to_vehicle(manager_client, active_trip):
    from apps.fleet.models import Vehicle

    other = Vehicle.objects.create(plate="OUT1B23", brand="VW", model="Delivery", year=2021)
    response = manager_client.post("/api/logistics/pings/", ping(other, trip=active_trip.id), format="json")
    assert response.status_code == 400


def test_live_returns_latest_position_per_vehicle(manager_client, vehicle):
    manager_client.post("/api/logistics/pings/", ping(vehicle, latitude=-8.0, recorded_at="2099-01-01T10:00:00Z"), format="json")
    manager_client.post("/api/logistics/pings/", ping(vehicle, latitude=-9.0), format="json")
    manager_client.post("/api/logistics/pings/", ping(vehicle, latitude=-7.0, recorded_at="2000-01-01T10:00:00Z"), format="json")
    rows = manager_client.get("/api/logistics/live/").data
    assert len(rows) == 1
    # recorded_at no futuro (2099) é o mais recente; o de 2000 está fora da janela de 24h
    assert rows[0]["latitude"] == -8.0


def test_track_returns_points_in_chronological_order(manager_client, active_trip, vehicle):
    for lat, ts in [(-9.0, "2026-01-01T12:00:00Z"), (-8.0, "2026-01-01T10:00:00Z"), (-8.5, "2026-01-01T11:00:00Z")]:
        manager_client.post("/api/logistics/pings/", ping(vehicle, trip=active_trip.id, latitude=lat, recorded_at=ts), format="json")
    points = manager_client.get(f"/api/logistics/trips/{active_trip.id}/track/").data
    assert [p["latitude"] for p in points] == [-8.0, -8.5, -9.0]


def test_realtime_failure_does_not_break_ingestion(manager_client, vehicle, monkeypatch):
    def boom():
        raise RuntimeError("redis fora do ar")

    monkeypatch.setattr("apps.logistics.realtime.get_channel_layer", boom)
    assert manager_client.post("/api/logistics/pings/", ping(vehicle), format="json").status_code == 201
