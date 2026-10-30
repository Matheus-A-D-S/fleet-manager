from rest_framework import viewsets

from apps.accounts.permissions import IsManager

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsManager]
    filterset_fields = ["model", "action", "user", "object_id"]
    search_fields = ["object_repr", "user_email"]
    ordering_fields = ["created_at"]
