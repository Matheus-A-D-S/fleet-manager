from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.alerts.models import Alert
from apps.alerts.services import scan_fleet
from apps.fleet.models import Driver, Vehicle
from apps.logistics.models import Trip

pytestmark = pytest.mark.django_db(transaction=True)

FAST = {"speed_kmh": 120, "latitude": -8.7, "longitude": -63.9}


def post_ping(client, vehicle, recorded_at, **override):
    body = {"vehicle": vehicle.id, "recorded_at": recorded_at, **FAST, **override}
    return client.post("/api/logistics/pings/", body, format="json")


def test_speeding_creates_one_alert_and_one_email_per_hour(manager_client, manager, vehicle):
    assert post_ping(manager_client, vehicle, "2026-03-01T10:05:00Z").status_code == 201
    assert post_ping(manager_client, vehicle, "2026-03-01T10:40:00Z").status_code == 201
    assert Alert.objects.filter(kind="SPEEDING").count() == 1
    assert len(mail.outbox) == 1 and mail.outbox[0].to == [manager.email]

    post_ping(manager_client, vehicle, "2026-03-01T11:10:00Z")  # outra hora: novo alerta
    assert Alert.objects.filter(kind="SPEEDING").count() == 2


def test_speed_below_limit_creates_nothing(manager_client, vehicle):
    post_ping(manager_client, vehicle, "2026-03-01T10:05:00Z", speed_kmh=80)
    assert Alert.objects.count() == 0 and mail.outbox == []


def test_alert_emails_go_only_to_verified_managers(manager_client, driver_user, vehicle):
    post_ping(manager_client, vehicle, "2026-03-01T10:05:00Z")
    recipients = {addr for m in mail.outbox for addr in m.to}
    assert driver_user.email not in recipients


def test_scan_creates_each_alert_once(manager, vehicle, driver):
    today = timezone.localdate()
    Vehicle.objects.filter(pk=vehicle.pk).update(
        insurance_expiry=today + timedelta(days=10), odometer_km=9800, next_maintenance_km=10000
    )
    Driver.objects.filter(pk=driver.pk).update(license_expiry=today + timedelta(days=5))

    assert scan_fleet() == 3  # seguro, revisão por km e CNH
    assert scan_fleet() == 0  # idempotente
    assert Alert.objects.count() == 3 and len(mail.outbox) == 3


def test_expired_documents_are_critical(manager, vehicle):
    Vehicle.objects.filter(pk=vehicle.pk).update(licensing_expiry=timezone.localdate() - timedelta(days=3))
    scan_fleet()
    assert Alert.objects.get(kind="DOCUMENT").severity == "CRITICAL"


def test_scan_flags_late_trips(manager, active_trip):
    Trip.objects.filter(pk=active_trip.pk).update(scheduled_arrival=timezone.now() - timedelta(hours=1))
    scan_fleet()
    assert Alert.objects.filter(kind="TRIP_DELAY", trip=active_trip).count() == 1


def test_resolved_alert_is_not_recreated_by_next_scan(manager_client, manager, vehicle):
    Vehicle.objects.filter(pk=vehicle.pk).update(insurance_expiry=timezone.localdate() + timedelta(days=3))
    scan_fleet()
    alert = Alert.objects.get()

    assert manager_client.post(f"/api/alerts/{alert.id}/resolve/").status_code == 200
    alert.refresh_from_db()
    assert alert.resolved and alert.resolved_at
    assert scan_fleet() == 0
    assert Alert.objects.count() == 1


def test_renewed_document_triggers_a_new_alert(manager, vehicle):
    today = timezone.localdate()
    Vehicle.objects.filter(pk=vehicle.pk).update(insurance_expiry=today + timedelta(days=3))
    scan_fleet()
    Vehicle.objects.filter(pk=vehicle.pk).update(insurance_expiry=today + timedelta(days=10))
    assert scan_fleet() == 1  # nova data de vencimento = novo problema


def test_alert_list_and_filters(manager_client, manager, vehicle):
    Vehicle.objects.filter(pk=vehicle.pk).update(insurance_expiry=timezone.localdate() + timedelta(days=3))
    scan_fleet()
    response = manager_client.get("/api/alerts/?resolved=false")
    assert response.status_code == 200 and response.data["count"] == 1
    assert response.data["results"][0]["vehicle_plate"] == vehicle.plate
