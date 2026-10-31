from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Organization
from apps.fleet.models import Driver, Vehicle
from apps.logistics.models import LocationPing, Trip

User = get_user_model()


def make_user(email, first_name, role, org, password):
    user, _ = User.objects.get_or_create(
        email=email, defaults=dict(first_name=first_name, role=role, organization=org, is_email_verified=True)
    )
    user.set_password(password)
    user.save()
    return user


def make_trip(org, vehicle, driver, manager, origin, destination, start_lat, start_lng, cargo):
    now = timezone.now()
    trip, created = Trip.objects.get_or_create(
        organization=org, origin=origin, destination=destination,
        defaults=dict(
            vehicle=vehicle, driver=driver, status="IN_PROGRESS", started_at=now - timedelta(hours=3),
            scheduled_start=now - timedelta(hours=3), scheduled_arrival=now + timedelta(hours=20),
            cargo_description=cargo, cargo_weight_kg=12000, created_by=manager,
        ),
    )
    if created:
        vehicle.status = "IN_USE"
        vehicle.save()
        for i in range(12):  # rota fictícia, ~um ponto a cada 15 min
            LocationPing.objects.create(
                organization=org, vehicle=vehicle, trip=trip, latitude=start_lat - i * 0.04,
                longitude=start_lng + i * 0.05, speed_kmh=70 + (i % 4) * 5,
                recorded_at=now - timedelta(minutes=15 * (12 - i)),
            )
    return trip


class Command(BaseCommand):
    help = "Cria duas empresas de demonstração (apenas para desenvolvimento)."

    def handle(self, *args, **opts):
        today = timezone.localdate()

        # ---------- Transportes Alfa ----------
        alfa, _ = Organization.objects.get_or_create(slug="transportes-alfa", defaults={"name": "Transportes Alfa"})
        gestor_alfa = make_user("gestor@alfa.local", "Gestor Alfa", "ADMIN", alfa, "Gestor@12345")
        motorista_alfa = make_user("motorista@alfa.local", "Carlos", "DRIVER", alfa, "Motorista@12345")

        v1, _ = Vehicle.objects.get_or_create(
            organization=alfa, plate="ABC1D23",
            defaults=dict(brand="Volvo", model="FH 540", year=2021, vehicle_type="TRUCK", odometer_km=119700,
                          next_maintenance_km=120000, insurance_expiry=today + timedelta(days=12), capacity_kg=32000),
        )
        Vehicle.objects.get_or_create(
            organization=alfa, plate="XYZ9K88",
            defaults=dict(brand="Mercedes-Benz", model="Sprinter", year=2022, vehicle_type="VAN", odometer_km=48000,
                          next_maintenance_date=today + timedelta(days=45), capacity_kg=1500),
        )
        Vehicle.objects.get_or_create(
            organization=alfa, plate="QWE4R56",
            defaults=dict(brand="Fiat", model="Strada", year=2020, vehicle_type="CAR", odometer_km=90500, capacity_kg=700),
        )
        d1, _ = Driver.objects.get_or_create(
            organization=alfa, license_number="01234567890",
            defaults=dict(full_name="Carlos Almeida", user=motorista_alfa, license_category="E",
                          license_expiry=today + timedelta(days=200), phone="(69) 99999-0001"),
        )
        Driver.objects.get_or_create(
            organization=alfa, license_number="09876543210",
            defaults=dict(full_name="Marina Souza", license_category="D",
                          license_expiry=today + timedelta(days=15), phone="(69) 99999-0002"),
        )
        make_trip(alfa, v1, d1, gestor_alfa, "Porto Velho, RO", "Cuiabá, MT", -8.76, -63.90, "Eletrodomésticos")

        # ---------- Logística Beta (outra empresa: dados completamente separados) ----------
        beta, _ = Organization.objects.get_or_create(slug="logistica-beta", defaults={"name": "Logística Beta"})
        gestor_beta = make_user("gestor@beta.local", "Gestor Beta", "ADMIN", beta, "Gestor@12345")
        v2, _ = Vehicle.objects.get_or_create(
            organization=beta, plate="BET1A11",
            defaults=dict(brand="Scania", model="R 450", year=2022, vehicle_type="TRUCK", odometer_km=30000,
                          licensing_expiry=today + timedelta(days=9), capacity_kg=28000),
        )
        d2, _ = Driver.objects.get_or_create(
            organization=beta, license_number="55555555555",
            defaults=dict(full_name="Paulo Ribeiro", license_category="E", license_expiry=today + timedelta(days=300)),
        )
        make_trip(beta, v2, d2, gestor_beta, "Manaus, AM", "Boa Vista, RR", 3.10, -60.00, "Bebidas")

        self.stdout.write(self.style.SUCCESS(
            "Pronto.\n"
            "  Transportes Alfa: gestor@alfa.local / Gestor@12345  |  motorista@alfa.local / Motorista@12345\n"
            "  Logística Beta:   gestor@beta.local / Gestor@12345"
        ))
