import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.fleet.models import Driver, Vehicle


class Trip(models.Model):
    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planejada"
        IN_PROGRESS = "IN_PROGRESS", "Em andamento"
        COMPLETED = "COMPLETED", "Concluída"
        CANCELLED = "CANCELLED", "Cancelada"

    code = models.CharField(max_length=24, unique=True, editable=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="trips")
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT, related_name="trips")
    origin = models.CharField("origem", max_length=255)
    destination = models.CharField("destino", max_length=255)
    origin_lat = models.FloatField(null=True, blank=True)
    origin_lng = models.FloatField(null=True, blank=True)
    dest_lat = models.FloatField(null=True, blank=True)
    dest_lng = models.FloatField(null=True, blank=True)
    cargo_description = models.TextField("carga", blank=True)
    cargo_weight_kg = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PLANNED, db_index=True)
    scheduled_start = models.DateTimeField()
    scheduled_arrival = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scheduled_start"]

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"TRP-{timezone.now():%y%m%d}-{uuid.uuid4().hex[:5].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class LocationPing(models.Model):
    """Ponto de rastreamento (GPS) enviado pelo app do motorista ou por um rastreador."""

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="pings")
    trip = models.ForeignKey(Trip, null=True, blank=True, on_delete=models.SET_NULL, related_name="pings")
    latitude = models.FloatField()
    longitude = models.FloatField()
    speed_kmh = models.FloatField(default=0)
    heading = models.FloatField(null=True, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [models.Index(fields=["vehicle", "-recorded_at"])]
