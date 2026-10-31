from datetime import timedelta

from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsManager, IsManagerOrReadOnly, IsTenantMember
from apps.alerts import services as alert_services
from apps.alerts.models import Alert
from apps.audit.mixins import AuditedMixin
from apps.audit.models import AuditLog
from apps.audit.services import record
from apps.core.tenancy import TenantQuerysetMixin
from apps.fleet.models import Driver, Vehicle

from . import realtime
from .models import LocationPing, Trip
from .serializers import LocationPingSerializer, TripSerializer


class TripViewSet(TenantQuerysetMixin, AuditedMixin, viewsets.ModelViewSet):
    queryset = Trip.objects.select_related("vehicle", "driver")
    serializer_class = TripSerializer
    permission_classes = [IsManagerOrReadOnly]
    filterset_fields = ["status", "vehicle", "driver"]
    search_fields = ["code", "origin", "destination", "vehicle__plate", "driver__full_name"]
    ordering_fields = ["scheduled_start", "scheduled_arrival", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()  # já restrito à empresa do usuário
        user = self.request.user
        # Motorista só enxerga as próprias viagens.
        if getattr(self, "swagger_fake_view", False) or user.role != "DRIVER":
            return qs
        return qs.filter(driver__user=user)

    def get_permissions(self):
        if self.action in ("start", "complete"):
            return [IsTenantMember()]  # motorista dono da viagem ou gestor (o queryset já restringe)
        return super().get_permissions()

    def get_create_kwargs(self):
        return {**super().get_create_kwargs(), "created_by": self.request.user}

    @transaction.atomic
    def _transition(self, request, allowed_from, new_status, vehicle_status, **extra):
        trip = self.get_object()
        if trip.status not in allowed_from:
            raise ValidationError({"detail": f"Não é possível mudar de '{trip.get_status_display()}' para este estado."})
        previous = trip.status
        trip.status = new_status
        for field, value in extra.items():
            setattr(trip, field, value)
        trip.save()
        if vehicle_status:
            Vehicle.objects.filter(pk=trip.vehicle_id).update(status=vehicle_status)
        record(request, AuditLog.Action.ACTION, trip, {"action": self.action, "status": {"from": previous, "to": new_status}})
        return Response(self.get_serializer(trip).data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        trip = self.get_object()
        if trip.vehicle.status in (Vehicle.Status.MAINTENANCE, Vehicle.Status.INACTIVE):
            raise ValidationError({"detail": "Veículo indisponível."})
        if trip.driver.license_expiry < timezone.localdate():
            raise ValidationError({"detail": "CNH do motorista vencida."})
        return self._transition(
            request, [Trip.Status.PLANNED], Trip.Status.IN_PROGRESS, Vehicle.Status.IN_USE, started_at=timezone.now()
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._transition(
            request, [Trip.Status.IN_PROGRESS], Trip.Status.COMPLETED, Vehicle.Status.AVAILABLE, finished_at=timezone.now()
        )

    @action(detail=True, methods=["post"], permission_classes=[IsManager])
    def cancel(self, request, pk=None):
        trip = self.get_object()
        vehicle_status = Vehicle.Status.AVAILABLE if trip.status == Trip.Status.IN_PROGRESS else None
        return self._transition(
            request, [Trip.Status.PLANNED, Trip.Status.IN_PROGRESS], Trip.Status.CANCELLED, vehicle_status
        )

    @action(detail=True, methods=["get"])
    def track(self, request, pk=None):
        trip = self.get_object()
        pings = trip.pings.order_by("recorded_at").values("latitude", "longitude", "speed_kmh", "recorded_at")
        return Response(list(pings))


class PingViewSet(TenantQuerysetMixin, mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = LocationPing.objects.select_related("vehicle", "trip")
    serializer_class = LocationPingSerializer
    filterset_fields = ["vehicle", "trip"]
    ordering_fields = ["recorded_at"]

    def get_permissions(self):
        return [IsTenantMember()] if self.action == "create" else [IsManager()]

    def perform_create(self, serializer):
        user = self.request.user
        vehicle = serializer.validated_data["vehicle"]  # o serializer só aceita veículos da empresa do usuário
        trip = serializer.validated_data.get("trip")

        if user.role == "DRIVER":
            # Motorista só reporta posição do veículo da própria viagem em andamento.
            trip = Trip.objects.filter(driver__user=user, vehicle=vehicle, status=Trip.Status.IN_PROGRESS).first()
            if not trip:
                raise PermissionDenied("Você não tem viagem em andamento com este veículo.")
        elif trip and trip.vehicle_id != vehicle.id:
            raise ValidationError({"trip": "A viagem não pertence a este veículo."})

        ping = serializer.save(trip=trip, organization_id=vehicle.organization_id)
        alert_services.check_speeding(ping)
        realtime.publish_position(ping)


class LiveFleetView(APIView):
    """Última posição conhecida de cada veículo da empresa (últimas 24h)."""

    permission_classes = [IsManager]

    def get(self, request):
        since = timezone.now() - timedelta(hours=24)
        pings = (
            LocationPing.objects.filter(organization_id=request.user.organization_id, recorded_at__gte=since)
            .select_related("vehicle", "trip")
            .order_by("vehicle_id", "-recorded_at")
            .distinct("vehicle_id")  # DISTINCT ON do PostgreSQL
        )
        return Response([realtime.live_payload(p) for p in pings])


class DashboardView(APIView):
    def get(self, request):
        org = request.user.organization_id

        def counts(qs):
            return {row["status"]: row["n"] for row in qs.values("status").annotate(n=Count("id"))}

        data = {
            "vehicles": counts(Vehicle.objects.filter(organization_id=org)),
            "trips": counts(Trip.objects.filter(organization_id=org)),
            "drivers_active": Driver.objects.filter(organization_id=org, is_active=True).count(),
        }
        if request.user.role in ("ADMIN", "MANAGER"):
            open_alerts = Alert.objects.filter(organization_id=org, resolved=False)
            data["open_alerts"] = open_alerts.count()
            data["critical_alerts"] = open_alerts.filter(severity=Alert.Severity.CRITICAL).count()
        return Response(data)
