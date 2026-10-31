from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.core.tenancy import TenantSerializerMixin

from .models import Driver, MaintenanceRecord, Vehicle


class VehicleSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    vehicle_type_display = serializers.CharField(source="get_vehicle_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Vehicle
        fields = "__all__"
        read_only_fields = ["organization"]

    def validate_plate(self, value):
        value = value.upper().replace("-", "").strip()
        duplicates = Vehicle.objects.filter(organization_id=self._org_id(), plate=value)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("Já existe um veículo com esta placa na sua empresa.")
        return value


class DriverSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    tenant_related = {"user": get_user_model()}
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Driver
        fields = "__all__"
        read_only_fields = ["organization"]

    def validate_license_number(self, value):
        duplicates = Driver.objects.filter(organization_id=self._org_id(), license_number=value)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("Já existe um motorista com esta CNH na sua empresa.")
        return value


class MaintenanceRecordSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    tenant_related = {"vehicle": Vehicle}
    vehicle_plate = serializers.CharField(source="vehicle.plate", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = MaintenanceRecord
        fields = "__all__"
        read_only_fields = ["organization"]
