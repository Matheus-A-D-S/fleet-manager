from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsManager
from apps.core.tenancy import TenantQuerysetMixin

from .models import Alert
from .serializers import AlertSerializer
from .tasks import scan_fleet_task


class AlertViewSet(TenantQuerysetMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Alert.objects.select_related("vehicle")
    serializer_class = AlertSerializer
    permission_classes = [IsManager]
    filterset_fields = ["kind", "severity", "resolved"]
    ordering_fields = ["created_at", "severity"]

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        if not alert.resolved:
            alert.resolved = True
            alert.resolved_at = timezone.now()
            alert.save(update_fields=["resolved", "resolved_at"])
        return Response(self.get_serializer(alert).data)

    @action(detail=False, methods=["post"])
    def scan(self, request):
        """Força a varredura agora (útil para testes)."""
        scan_fleet_task.delay()
        return Response({"detail": "Varredura enfileirada."}, status=202)
