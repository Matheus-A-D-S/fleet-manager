from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.fleet.models import Driver, Vehicle
from apps.logistics.models import Trip

PASSWORD = "Senha@12345"


def make_user(email, role, **extra):
    return User.objects.create_user(email=email, password=PASSWORD, role=role, is_email_verified=True, **extra)


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def manager():
    return make_user("gestor@test.com", "MANAGER")


@pytest.fixture
def driver_user():
    return make_user("motorista@test.com", "DRIVER")


@pytest.fixture
def manager_client(manager):
    return client_for(manager)


@pytest.fixture
def driver_client(driver_user):
    return client_for(driver_user)


@pytest.fixture
def vehicle():
    return Vehicle.objects.create(plate="TST1A23", brand="Volvo", model="FH 540", year=2022, odometer_km=1000)


@pytest.fixture
def driver(driver_user):
    return Driver.objects.create(
        full_name="Carlos Almeida",
        license_number="11111111111",
        license_expiry=timezone.localdate() + timedelta(days=365),
        user=driver_user,
    )


@pytest.fixture
def active_trip(vehicle, driver):
    now = timezone.now()
    vehicle.status = Vehicle.Status.IN_USE
    vehicle.save()
    return Trip.objects.create(
        vehicle=vehicle,
        driver=driver,
        origin="Porto Velho",
        destination="Cuiabá",
        scheduled_start=now,
        scheduled_arrival=now + timedelta(hours=4),
        status=Trip.Status.IN_PROGRESS,
    )
