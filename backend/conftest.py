from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.fleet.models import Driver, Vehicle
from apps.logistics.models import Trip

PASSWORD = "Senha@12345"


def make_user(email, role, org=None, **extra):
    return User.objects.create_user(
        email=email, password=PASSWORD, role=role, organization=org, is_email_verified=True, **extra
    )


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def link_params(body, marker):
    """Extrai os parâmetros (uid/token...) do link de um e-mail."""
    link = next(line for line in body.splitlines() if marker in line)
    return {k: v[0] for k, v in parse_qs(urlparse(link).query).items()}


def trip_payload(vehicle, driver, **override):
    now = timezone.now()
    payload = {
        "vehicle": vehicle.id,
        "driver": driver.id,
        "origin": "Porto Velho",
        "destination": "Cuiabá",
        "scheduled_start": (now + timedelta(hours=1)).isoformat(),
        "scheduled_arrival": (now + timedelta(hours=5)).isoformat(),
    }
    payload.update(override)
    return payload


# ---------- empresa A (a "nossa") ----------
@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="Transportes Alfa", slug="alfa")


@pytest.fixture
def admin_user(org):
    return make_user("admin@test.com", "ADMIN", org)


@pytest.fixture
def manager(org):
    return make_user("gestor@test.com", "MANAGER", org)


@pytest.fixture
def driver_user(org):
    return make_user("motorista@test.com", "DRIVER", org)


@pytest.fixture
def admin_client(admin_user):
    return client_for(admin_user)


@pytest.fixture
def manager_client(manager):
    return client_for(manager)


@pytest.fixture
def driver_client(driver_user):
    return client_for(driver_user)


@pytest.fixture
def vehicle(org):
    return Vehicle.objects.create(organization=org, plate="TST1A23", brand="Volvo", model="FH 540", year=2022, odometer_km=1000)


@pytest.fixture
def driver(org, driver_user):
    return Driver.objects.create(
        organization=org,
        full_name="Carlos Almeida",
        license_number="11111111111",
        license_expiry=timezone.localdate() + timedelta(days=365),
        user=driver_user,
    )


@pytest.fixture
def active_trip(org, vehicle, driver):
    now = timezone.now()
    vehicle.status = Vehicle.Status.IN_USE
    vehicle.save()
    return Trip.objects.create(
        organization=org,
        vehicle=vehicle,
        driver=driver,
        origin="Porto Velho",
        destination="Cuiabá",
        scheduled_start=now,
        scheduled_arrival=now + timedelta(hours=4),
        status=Trip.Status.IN_PROGRESS,
    )


# ---------- empresa B (a "vizinha": nada dela pode vazar para a A) ----------
@pytest.fixture
def other_org():
    return Organization.objects.create(name="Logística Beta", slug="beta")


@pytest.fixture
def other_manager(other_org):
    return make_user("gestor@beta.test", "MANAGER", other_org)


@pytest.fixture
def other_manager_client(other_manager):
    return client_for(other_manager)


@pytest.fixture
def other_vehicle(other_org):
    return Vehicle.objects.create(organization=other_org, plate="BET1A11", brand="Scania", model="R 450", year=2022)


@pytest.fixture
def other_driver(other_org):
    return Driver.objects.create(
        organization=other_org,
        full_name="Paulo Ribeiro",
        license_number="55555555555",
        license_expiry=timezone.localdate() + timedelta(days=300),
    )
