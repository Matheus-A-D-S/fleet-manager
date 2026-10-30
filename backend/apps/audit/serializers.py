from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id", "created_at", "user", "user_email", "action", "action_display", "model",
            "object_id", "object_repr", "changes", "ip_address", "request_id",
        ]
        read_only_fields = fields
