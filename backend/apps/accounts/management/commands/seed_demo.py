from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.fleet.models import Driver, Vehicle
from apps.logistics.models import LocationPing, Trip


class Command(BaseCommand):
    help = "Cria dados de demonstração (apenas para desenvolvimento)."

    def handle(self, *args, **opts):
        User = get_user_model()
        today = timezone.localdate()
        now = timezone.now()

        mgr, _ = User.objects.get_or_create(
            email="gestor@fleet.local",
            defaults=dict(first_name="Gestor", role="MANAGER", is_email_verified=True),
        )
        mgr.set_password("Gestor@12345")
        mgr.save()
        drv_user, _ = User.objects.get_or_create(
            email="motorista@fleet.local",
            defaults=dict(first_name="Carlos", role="DRIVER", is_email_verified=True),
        )
        drv_user.set_password("Motorista@12345")
        drv_user.save()

        v1, _ = Vehicle.objects.get_or_create(
            plate="ABC1D23",
            defaults=dict(brand="Volvo", model="FH 540", year=2021, vehicle_type="TRUCK", odometer_km=119700,
                          next_maintenance_km=120000, insurance_expiry=today + timedelta(days=12), capacity_kg=32000),
        )
        v2, _ = Vehicle.objects.get_or_create(
            plate="XYZ9K88",
            defaults=dict(brand="Mercedes-Benz", model="Sprinter", year=2022, vehicle_type="VAN", odometer_km=48000,
                          next_maintenance_date=today + timedelta(days=45), capacity_kg=1500),
        )
        Vehicle.objects.get_or_create(
            plate="QWE4R56",
            defaults=dict(brand="Fiat", model="Strada", year=2020, vehicle_type="CAR", odometer_km=90500, capacity_kg=700),
        )
        d1, _ = Driver.objects.get_or_create(
            license_number="01234567890",
            defaults=dict(full_name="Carlos Almeida", user=drv_user, license_category="E",
                          license_expiry=today + timedelta(days=200), phone="(69) 99999-0001"),
        )
        Driver.objects.get_or_create(
            license_number="09876543210",
            defaults=dict(full_name="Marina Souza", license_category="D",
                          license_expiry=today + timedelta(days=15), phone="(69) 99999-0002"),
        )

        trip, created = Trip.objects.get_or_create(
            origin="Porto Velho, RO", destination="Cuiabá, MT",
            defaults=dict(vehicle=v1, driver=d1, status="IN_PROGRESS", started_at=now - timedelta(hours=3),
                          scheduled_start=now - timedelta(hours=3), scheduled_arrival=now + timedelta(hours=20),
                          cargo_description="Eletrodomésticos", cargo_weight_kg=18000, created_by=mgr),
        )
        if created:
            v1.status = "IN_USE"
            v1.save()
            lat, lng = -8.76, -63.90
            for i in range(12):  # rota fictícia, ~um ponto a cada 15 min
                LocationPing.objects.create(
                    vehicle=v1, trip=trip, latitude=lat - i * 0.04, longitude=lng + i * 0.05,
                    speed_kmh=70 + (i % 4) * 5, recorded_at=now - timedelta(minutes=15 * (12 - i)),
                )
        self.stdout.write(self.style.SUCCESS(
            "Pronto. Gestor: gestor@fleet.local / Gestor@12345 | Motorista: motorista@fleet.local / Motorista@12345"
        ))
