import pytest

from apps.audit.models import AuditLog

pytestmark = pytest.mark.django_db(transaction=True)


def test_create_update_delete_are_audited(manager_client, manager):
    created = manager_client.post(
        "/api/fleet/vehicles/", {"plate": "AUD1T23", "brand": "VW", "model": "Delivery", "year": 2022, "odometer_km": 1000}, format="json"
    )
    vid = created.data["id"]
    manager_client.patch(f"/api/fleet/vehicles/{vid}/", {"odometer_km": 2000}, format="json")
    manager_client.delete(f"/api/fleet/vehicles/{vid}/")

    logs = list(AuditLog.objects.order_by("id"))
    assert [log.action for log in logs] == ["CREATE", "UPDATE", "DELETE"]
    assert all(log.user == manager and log.user_email == manager.email for log in logs)
    assert logs[1].changes == {"odometer_km": {"from": 1000, "to": 2000}}
    assert logs[2].object_repr.startswith("AUD1T23")  # identificação preservada após a exclusão


def test_trip_transitions_are_audited(manager_client, active_trip):
    manager_client.post(f"/api/logistics/trips/{active_trip.id}/complete/")
    log = AuditLog.objects.get(action="ACTION")
    assert log.changes == {"action": "complete", "status": {"from": "IN_PROGRESS", "to": "COMPLETED"}}


def test_failed_delete_is_not_audited(manager_client, active_trip):
    manager_client.delete(f"/api/fleet/vehicles/{active_trip.vehicle_id}/")  # 409: há viagens vinculadas
    assert not AuditLog.objects.filter(action="DELETE").exists()


def test_audit_endpoint_filters_by_model(manager_client, vehicle):
    manager_client.patch(f"/api/fleet/vehicles/{vehicle.id}/", {"odometer_km": 5}, format="json")
    response = manager_client.get("/api/audit/?model=fleet.Vehicle")
    assert response.status_code == 200 and response.data["count"] == 1
    assert manager_client.get("/api/audit/?model=fleet.Driver").data["count"] == 0
