from rest_framework import serializers

from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    vehicle_plate = serializers.CharField(source="vehicle.plate", read_only=True, default=None)

    class Meta:
        model = Alert
        fields = "__all__"
