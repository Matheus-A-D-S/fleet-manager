"""Isolamento entre empresas: nada de uma pode ser visto, alterado ou referenciado pela outra."""
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.accounts.models import User
from apps.alerts.services import scan_fleet
from apps.fleet.models import Vehicle
from apps.logistics.models import LocationPing
from conftest import PASSWORD, link_params, trip_payload

pytestmark = pytest.mark.django_db(transaction=True)


# ---------------------------------------------------------------- dados
def test_lists_and_details_are_scoped_to_own_company(manager_client, vehicle, other_vehicle):
    ids = [v["id"] for v in manager_client.get("/api/fleet/vehicles/").data["results"]]
    assert ids == [vehicle.id]
    url = f"/api/fleet/vehicles/{other_vehicle.id}/"
    assert manager_client.get(url).status_code == 404
    assert manager_client.patch(url, {"odometer_km": 1}, format="json").status_code == 404
    assert manager_client.delete(url).status_code == 404
    other_vehicle.refresh_from_db()  # continua intacto
    assert other_vehicle.odometer_km == 0


def test_new_records_are_created_in_the_users_company(manager_client, org):
    response = manager_client.post(
        "/api/fleet/vehicles/", {"plate": "NEW1A11", "brand": "VW", "model": "Delivery", "year": 2023}, format="json"
    )
    assert response.status_code == 201
    assert Vehicle.objects.get(pk=response.data["id"]).organization == org


def test_organization_cannot_be_chosen_by_the_client(manager_client, org, other_org):
    body = {"plate": "HAC1K33", "brand": "VW", "model": "Delivery", "year": 2023, "organization": other_org.id}
    response = manager_client.post("/api/fleet/vehicles/", body, format="json")
    assert response.status_code == 201
    assert Vehicle.objects.get(pk=response.data["id"]).organization == org  # o campo enviado é ignorado


def test_same_plate_is_allowed_across_companies_but_not_within_one(manager_client, vehicle, other_vehicle):
    body = {"plate": other_vehicle.plate, "brand": "VW", "model": "X", "year": 2023}
    assert manager_client.post("/api/fleet/vehicles/", body, format="json").status_code == 201
    assert manager_client.post("/api/fleet/vehicles/", body, format="json").status_code == 400


def test_same_driver_license_is_allowed_across_companies_but_not_within_one(manager_client, driver, other_driver):
    body = {"full_name": "Fulano", "license_number": other_driver.license_number, "license_expiry": "2030-01-01"}
    assert manager_client.post("/api/fleet/drivers/", body, format="json").status_code == 201
    assert manager_client.post("/api/fleet/drivers/", body, format="json").status_code == 400


def test_cannot_reference_objects_of_another_company(manager_client, vehicle, driver, other_vehicle, other_driver, other_manager):
    trips = "/api/logistics/trips/"
    assert manager_client.post(trips, trip_payload(other_vehicle, driver), format="json").status_code == 400
    assert manager_client.post(trips, trip_payload(vehicle, other_driver), format="json").status_code == 400

    ping = {"vehicle": other_vehicle.id, "latitude": -8.7, "longitude": -63.9, "speed_kmh": 50}
    assert manager_client.post("/api/logistics/pings/", ping, format="json").status_code == 400
    assert LocationPing.objects.count() == 0

    maintenance = {"vehicle": other_vehicle.id, "description": "x", "odometer_km": 1, "performed_at": "2026-01-01"}
    assert manager_client.post("/api/fleet/maintenance/", maintenance, format="json").status_code == 400

    link_user = {"full_name": "Fulano", "license_number": "999", "license_expiry": "2030-01-01", "user": other_manager.id}
    assert manager_client.post("/api/fleet/drivers/", link_user, format="json").status_code == 400


def test_dashboard_counts_only_own_company(manager_client, vehicle, other_vehicle, other_org):
    Vehicle.objects.create(organization=other_org, plate="BET2B22", brand="X", model="Y", year=2020)
    data = manager_client.get("/api/logistics/dashboard/").data
    assert data["vehicles"] == {"AVAILABLE": 1}


def test_live_map_shows_only_own_vehicles(manager_client, org, other_org, vehicle, other_vehicle):
    for o, v in ((org, vehicle), (other_org, other_vehicle)):
        LocationPing.objects.create(organization=o, vehicle=v, latitude=-8.0, longitude=-63.0, speed_kmh=40)
    rows = manager_client.get("/api/logistics/live/").data
    assert [r["plate"] for r in rows] == [vehicle.plate]


# ---------------------------------------------------------------- alertas e auditoria
def test_alerts_and_emails_stay_inside_each_company(manager_client, manager, other_manager, vehicle, other_vehicle):
    soon = timezone.localdate() + timedelta(days=3)
    Vehicle.objects.filter(pk__in=[vehicle.pk, other_vehicle.pk]).update(insurance_expiry=soon)

    assert scan_fleet() == 2
    by_recipient = {m.to[0]: m.subject for m in mail.outbox}
    assert vehicle.plate in by_recipient[manager.email] and other_vehicle.plate not in by_recipient[manager.email]
    assert other_vehicle.plate in by_recipient[other_manager.email]

    mine = manager_client.get("/api/alerts/").data
    assert mine["count"] == 1 and mine["results"][0]["vehicle_plate"] == vehicle.plate


def test_audit_trail_is_scoped_to_company(manager_client, other_manager_client, vehicle):
    other_manager_client.post("/api/fleet/vehicles/", {"plate": "BET9Z99", "brand": "X", "model": "Y", "year": 2020}, format="json")
    manager_client.patch(f"/api/fleet/vehicles/{vehicle.id}/", {"odometer_km": 7}, format="json")
    mine = manager_client.get("/api/audit/").data
    assert mine["count"] == 1 and mine["results"][0]["object_repr"].startswith(vehicle.plate)


# ---------------------------------------------------------------- usuários e convites
def test_admin_invites_user_who_sets_a_password_by_email(admin_client, org, api):
    body = {"email": "novo@alfa.test", "first_name": "Novo", "role": "MANAGER"}
    response = admin_client.post("/api/auth/users/", body, format="json")
    assert response.status_code == 201

    invited = User.objects.get(email="novo@alfa.test")
    assert invited.organization == org and invited.role == "MANAGER" and not invited.has_usable_password()
    assert mail.outbox[0].to == ["novo@alfa.test"] and org.name in mail.outbox[0].subject

    params = link_params(mail.outbox[0].body, "reset-password")
    assert api.post("/api/auth/password-reset/confirm/", {**params, "password": "NovaSenha@2026"}, format="json").status_code == 200
    login = api.post("/api/auth/login/", {"email": "novo@alfa.test", "password": "NovaSenha@2026"}, format="json")
    assert login.status_code == 200 and login.data["user"]["organization_name"] == org.name


def test_only_the_company_admin_manages_users(manager_client, driver_client):
    body = {"email": "x@alfa.test", "first_name": "X", "role": "DRIVER"}
    assert manager_client.post("/api/auth/users/", body, format="json").status_code == 403
    assert driver_client.post("/api/auth/users/", body, format="json").status_code == 403
    assert manager_client.get("/api/auth/users/").status_code == 200  # gestor consulta a equipe
    assert driver_client.get("/api/auth/users/").status_code == 403


def test_admin_only_sees_and_edits_own_company_users(admin_client, other_manager, manager):
    emails = [u["email"] for u in admin_client.get("/api/auth/users/").data["results"]]
    assert manager.email in emails and other_manager.email not in emails
    assert admin_client.patch(f"/api/auth/users/{other_manager.id}/", {"role": "DRIVER"}, format="json").status_code == 404


def test_admin_cannot_demote_or_deactivate_self(admin_client, admin_user):
    url = f"/api/auth/users/{admin_user.id}/"
    assert admin_client.patch(url, {"role": "MANAGER"}, format="json").status_code == 400
    assert admin_client.patch(url, {"is_active": False}, format="json").status_code == 400


def test_deactivated_user_loses_access(admin_client, manager, api):
    assert admin_client.patch(f"/api/auth/users/{manager.id}/", {"is_active": False}, format="json").status_code == 200
    login = api.post("/api/auth/login/", {"email": manager.email, "password": PASSWORD}, format="json")
    assert login.status_code == 401


def test_resend_invite_only_for_pending_users(admin_client, manager):
    admin_client.post("/api/auth/users/", {"email": "pend@alfa.test", "first_name": "P", "role": "DRIVER"}, format="json")
    pending = User.objects.get(email="pend@alfa.test")
    assert admin_client.post(f"/api/auth/users/{pending.id}/resend-invite/").status_code == 200
    assert len(mail.outbox) == 2
    assert admin_client.post(f"/api/auth/users/{manager.id}/resend-invite/").status_code == 400  # já ativo


def test_user_changes_are_audited_without_leaking_password_hash(admin_client, manager):
    from apps.audit.models import AuditLog

    admin_client.patch(f"/api/auth/users/{manager.id}/", {"role": "DRIVER"}, format="json")
    log = AuditLog.objects.get(model="accounts.User")
    assert log.changes == {"role": {"from": "MANAGER", "to": "DRIVER"}}
    admin_client.post("/api/auth/users/", {"email": "n@alfa.test", "first_name": "N", "role": "DRIVER"}, format="json")
    created = AuditLog.objects.get(model="accounts.User", action="CREATE")
    assert "password" not in created.changes
