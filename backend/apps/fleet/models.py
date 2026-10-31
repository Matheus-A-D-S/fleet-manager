from django.conf import settings
from django.db import models


class Vehicle(models.Model):
    class Type(models.TextChoices):
        TRUCK = "TRUCK", "Caminhão"
        VAN = "VAN", "Van"
        CAR = "CAR", "Carro"
        MOTORCYCLE = "MOTORCYCLE", "Moto"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Disponível"
        IN_USE = "IN_USE", "Em viagem"
        MAINTENANCE = "MAINTENANCE", "Em manutenção"
        INACTIVE = "INACTIVE", "Inativo"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.PROTECT, related_name="vehicles")
    plate = models.CharField("placa", max_length=10)
    brand = models.CharField("marca", max_length=60)
    model = models.CharField("modelo", max_length=60)
    year = models.PositiveSmallIntegerField("ano")
    vehicle_type = models.CharField(max_length=12, choices=Type.choices, default=Type.TRUCK)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    odometer_km = models.PositiveIntegerField("odômetro (km)", default=0)
    capacity_kg = models.PositiveIntegerField("capacidade (kg)", null=True, blank=True)
    next_maintenance_km = models.PositiveIntegerField(null=True, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)
    insurance_expiry = models.DateField("vencimento do seguro", null=True, blank=True)
    licensing_expiry = models.DateField("vencimento do licenciamento", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["plate"]
        constraints = [models.UniqueConstraint(fields=["organization", "plate"], name="uniq_vehicle_plate_per_org")]

    def save(self, *args, **kwargs):
        self.plate = self.plate.upper().replace("-", "").strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plate} - {self.brand} {self.model}"


class Driver(models.Model):
    class Category(models.TextChoices):
        A = "A", "A"
        B = "B", "B"
        C = "C", "C"
        D = "D", "D"
        E = "E", "E"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.PROTECT, related_name="drivers")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="driver_profile"
    )
    full_name = models.CharField("nome completo", max_length=120)
    license_number = models.CharField("CNH", max_length=20)
    license_category = models.CharField(max_length=2, choices=Category.choices, default=Category.C)
    license_expiry = models.DateField("validade da CNH")
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]
        constraints = [models.UniqueConstraint(fields=["organization", "license_number"], name="uniq_driver_license_per_org")]

    def __str__(self):
        return self.full_name


class MaintenanceRecord(models.Model):
    class Kind(models.TextChoices):
        PREVENTIVE = "PREVENTIVE", "Preventiva"
        CORRECTIVE = "CORRECTIVE", "Corretiva"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.PROTECT, related_name="maintenance_records")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="maintenance_records")
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.PREVENTIVE)
    description = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    odometer_km = models.PositiveIntegerField()
    performed_at = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-performed_at", "-id"]

    def __str__(self):
        return f"{self.vehicle.plate} - {self.get_kind_display()} em {self.performed_at}"
