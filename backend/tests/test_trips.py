from datetime import timedelta

import pytest
from django.utils import timezone

from apps.fleet.models import Driver, Vehicle
from apps.logistics.models import Trip
from conftest import client_for, make_user, trip_payload

pytestmark = pytest.mark.django_db(transaction=True)


def test_create_trip_generates_code_and_records_creator(manager_client, manager, org, vehicle, driver):
    response = manager_client.post("/api/logistics/trips/", trip_payload(vehicle, driver), format="json")
    assert response.status_code == 201
    assert response.data["code"].startswith("TRP-")
    assert response.data["status"] == "PLANNED"
    trip = Trip.objects.get(pk=response.data["id"])
    assert trip.created_by == manager and trip.organization == org


def test_trip_validations(manager_client, vehicle, driver):
    now = timezone.now()
    backwards = trip_payload(vehicle, driver, scheduled_arrival=(now - timedelta(hours=2)).isoformat())
    assert manager_client.post("/api/logistics/trips/", backwards, format="json").status_code == 400

    Vehicle.objects.filter(pk=vehicle.pk).update(status="MAINTENANCE")
    assert manager_client.post("/api/logistics/trips/", trip_payload(vehicle, driver), format="json").status_code == 400

    Vehicle.objects.filter(pk=vehicle.pk).update(status="AVAILABLE")
    Driver.objects.filter(pk=driver.pk).update(license_expiry=timezone.localdate() - timedelta(days=1))
    assert manager_client.post("/api/logistics/trips/", trip_payload(vehicle, driver), format="json").status_code == 400


def test_full_trip_lifecycle_updates_vehicle_status(manager_client, vehicle, driver):
    trip_id = manager_client.post("/api/logistics/trips/", trip_payload(vehicle, driver), format="json").data["id"]

    started = manager_client.post(f"/api/logistics/trips/{trip_id}/start/")
    assert started.status_code == 200 and started.data["status"] == "IN_PROGRESS"
    vehicle.refresh_from_db()
    assert vehicle.status == "IN_USE"

    assert manager_client.post(f"/api/logistics/trips/{trip_id}/start/").status_code == 400  # já iniciada

    done = manager_client.post(f"/api/logistics/trips/{trip_id}/complete/")
    assert done.status_code == 200 and done.data["finished_at"]
    vehicle.refresh_from_db()
    assert vehicle.status == "AVAILABLE"


def test_cancel_in_progress_trip_frees_vehicle(manager_client, active_trip):
    assert manager_client.post(f"/api/logistics/trips/{active_trip.id}/cancel/").status_code == 200
    active_trip.vehicle.refresh_from_db()
    assert active_trip.vehicle.status == "AVAILABLE"


def test_driver_sees_and_operates_only_own_trips(driver_client, org, active_trip, vehicle):
    other_user = make_user("outro@test.com", "DRIVER", org)
    other_driver = Driver.objects.create(
        organization=org, full_name="Outro", license_number="22222222222", user=other_user,
        license_expiry=timezone.localdate() + timedelta(days=100),
    )
    foreign = Trip.objects.create(
        organization=org, vehicle=vehicle, driver=other_driver, origin="A", destination="B",
        scheduled_start=timezone.now(), scheduled_arrival=timezone.now() + timedelta(hours=2),
    )

    listed = driver_client.get("/api/logistics/trips/").data["results"]
    assert [t["id"] for t in listed] == [active_trip.id]
    assert driver_client.post(f"/api/logistics/trips/{foreign.id}/start/").status_code == 404
    assert driver_client.post(f"/api/logistics/trips/{active_trip.id}/complete/").status_code == 200


def test_driver_cannot_cancel_or_create_trips(driver_client, active_trip, vehicle, driver):
    assert driver_client.post(f"/api/logistics/trips/{active_trip.id}/cancel/").status_code == 403
    assert driver_client.post("/api/logistics/trips/", trip_payload(vehicle, driver), format="json").status_code == 403


def test_other_driver_client_helper_is_isolated(org, vehicle):
    stranger = client_for(make_user("estranho@test.com", "DRIVER", org))
    assert stranger.get("/api/logistics/trips/").data["results"] == []
