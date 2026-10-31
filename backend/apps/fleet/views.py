from rest_framework import viewsets

from apps.accounts.permissions import IsManagerOrReadOnly
from apps.audit.mixins import AuditedMixin
from apps.core.tenancy import TenantQuerysetMixin

from .models import Driver, MaintenanceRecord, Vehicle
from .serializers import DriverSerializer, MaintenanceRecordSerializer, VehicleSerializer


class VehicleViewSet(TenantQuerysetMixin, AuditedMixin, viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsManagerOrReadOnly]
    filterset_fields = ["status", "vehicle_type"]
    search_fields = ["plate", "brand", "model"]
    ordering_fields = ["plate", "odometer_km", "created_at"]


class DriverViewSet(TenantQuerysetMixin, AuditedMixin, viewsets.ModelViewSet):
    queryset = Driver.objects.select_related("user")
    serializer_class = DriverSerializer
    permission_classes = [IsManagerOrReadOnly]
    filterset_fields = ["is_active", "license_category"]
    search_fields = ["full_name", "license_number"]
    ordering_fields = ["full_name", "license_expiry"]


class MaintenanceRecordViewSet(TenantQuerysetMixin, AuditedMixin, viewsets.ModelViewSet):
    queryset = MaintenanceRecord.objects.select_related("vehicle")
    serializer_class = MaintenanceRecordSerializer
    permission_classes = [IsManagerOrReadOnly]
    filterset_fields = ["vehicle", "kind"]
    ordering_fields = ["performed_at", "cost"]
