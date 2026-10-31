import pytest

pytestmark = pytest.mark.django_db(transaction=True)

NEW_VEHICLE = {"plate": "abc-1234", "brand": "Fiat", "model": "Strada", "year": 2023}


def test_anonymous_gets_401(api):
    assert api.get("/api/fleet/vehicles/").status_code == 401
    assert api.get("/api/logistics/dashboard/").status_code == 401


def test_manager_can_create_vehicle_and_plate_is_normalized(manager_client):
    response = manager_client.post("/api/fleet/vehicles/", NEW_VEHICLE, format="json")
    assert response.status_code == 201
    assert response.data["plate"] == "ABC1234"


def test_driver_can_read_but_not_write_fleet(driver_client, vehicle):
    assert driver_client.get("/api/fleet/vehicles/").status_code == 200
    assert driver_client.post("/api/fleet/vehicles/", NEW_VEHICLE, format="json").status_code == 403
    assert driver_client.delete(f"/api/fleet/vehicles/{vehicle.id}/").status_code == 403


def test_driver_cannot_access_manager_areas(driver_client):
    assert driver_client.get("/api/alerts/").status_code == 403
    assert driver_client.get("/api/audit/").status_code == 403
    assert driver_client.get("/api/logistics/live/").status_code == 403
    assert driver_client.get("/api/auth/users/").status_code == 403


def test_deleting_vehicle_with_trips_returns_409(manager_client, active_trip):
    response = manager_client.delete(f"/api/fleet/vehicles/{active_trip.vehicle_id}/")
    assert response.status_code == 409


def test_dashboard_hides_alert_counters_from_drivers(driver_client, manager_client):
    assert "open_alerts" not in driver_client.get("/api/logistics/dashboard/").data
    assert "open_alerts" in manager_client.get("/api/logistics/dashboard/").data


def test_platform_superuser_without_company_has_no_tenant_access(api):
    from apps.accounts.models import User
    from conftest import client_for

    root = client_for(User.objects.create_superuser(email="root@test.com", password="x"))
    assert root.get("/api/fleet/vehicles/").status_code == 403
    assert root.get("/api/logistics/dashboard/").status_code == 403
    assert root.get("/api/auth/me/").status_code == 200  # ainda consulta o próprio perfil
