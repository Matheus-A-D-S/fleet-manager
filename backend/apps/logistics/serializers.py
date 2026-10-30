from django.utils import timezone
from rest_framework import serializers

from apps.fleet.models import Vehicle

from .models import LocationPing, Trip


class TripSerializer(serializers.ModelSerializer):
    vehicle_plate = serializers.CharField(source="vehicle.plate", read_only=True)
    driver_name = serializers.CharField(source="driver.full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Trip
        fields = "__all__"
        read_only_fields = ["code", "status", "started_at", "finished_at", "created_by"]

    def validate(self, attrs):
        start = attrs.get("scheduled_start", getattr(self.instance, "scheduled_start", None))
        arrival = attrs.get("scheduled_arrival", getattr(self.instance, "scheduled_arrival", None))
        if start and arrival and arrival <= start:
            raise serializers.ValidationError({"scheduled_arrival": "A chegada deve ser depois da saída."})

        vehicle = attrs.get("vehicle")
        if vehicle and vehicle.status in (Vehicle.Status.MAINTENANCE, Vehicle.Status.INACTIVE):
            raise serializers.ValidationError({"vehicle": "Veículo em manutenção ou inativo."})

        driver = attrs.get("driver")
        if driver:
            if not driver.is_active:
                raise serializers.ValidationError({"driver": "Motorista inativo."})
            if driver.license_expiry < timezone.localdate():
                raise serializers.ValidationError({"driver": "CNH vencida."})
        return attrs


class LocationPingSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationPing
        fields = ["id", "vehicle", "trip", "latitude", "longitude", "speed_kmh", "heading", "recorded_at"]
        read_only_fields = ["id"]
        extra_kwargs = {"trip": {"required": False}, "recorded_at": {"required": False}}

    def validate_latitude(self, v):
        if not -90 <= v <= 90:
            raise serializers.ValidationError("Latitude deve estar entre -90 e 90.")
        return v

    def validate_longitude(self, v):
        if not -180 <= v <= 180:
            raise serializers.ValidationError("Longitude deve estar entre -180 e 180.")
        return v

    def validate_speed_kmh(self, v):
        if v < 0 or v > 300:
            raise serializers.ValidationError("Velocidade fora do intervalo válido.")
        return v
