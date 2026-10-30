from rest_framework import serializers

from .models import Driver, MaintenanceRecord, Vehicle


class VehicleSerializer(serializers.ModelSerializer):
    vehicle_type_display = serializers.CharField(source="get_vehicle_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Vehicle
        fields = "__all__"


class DriverSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Driver
        fields = "__all__"


class MaintenanceRecordSerializer(serializers.ModelSerializer):
    vehicle_plate = serializers.CharField(source="vehicle.plate", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = MaintenanceRecord
        fields = "__all__"
