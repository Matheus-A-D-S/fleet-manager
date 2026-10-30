from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.fleet.models import Driver, Vehicle
from apps.logistics.models import Trip

from .models import Alert


def raise_alert(*, kind, severity, title, message, dedupe_key, vehicle=None, driver=None, trip=None):
    """Cria o alerta se a chave ainda não existir (aberto ou resolvido); e-mail só na criação."""
    from .tasks import send_alert_email

    alert, created = Alert.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults=dict(kind=kind, severity=severity, title=title, message=message, vehicle=vehicle, driver=driver, trip=trip),
    )
    if created:
        transaction.on_commit(lambda: send_alert_email.delay(alert.pk))
    return alert, created


def check_speeding(ping):
    if ping.speed_kmh <= settings.SPEED_LIMIT_KMH:
        return
    plate = ping.vehicle.plate
    raise_alert(
        kind=Alert.Kind.SPEEDING,
        severity=Alert.Severity.WARNING,
        title=f"Excesso de velocidade: {plate}",
        message=f"{plate} registrou {ping.speed_kmh:.0f} km/h (limite {settings.SPEED_LIMIT_KMH} km/h).",
        dedupe_key=f"speeding:{ping.vehicle_id}:{ping.recorded_at:%Y%m%d%H}",  # 1 alerta por veículo/hora
        vehicle=ping.vehicle,
        trip=ping.trip,
    )


def _expiry_severity(day, today):
    return Alert.Severity.CRITICAL if day < today else Alert.Severity.WARNING


def scan_fleet():
    """Varredura periódica (Celery beat): manutenção, documentos e viagens atrasadas."""
    now = timezone.now()
    today = timezone.localdate()
    horizon = today + timedelta(days=settings.ALERT_DAYS_BEFORE_EXPIRY)
    created = 0

    def add(**kw):
        nonlocal created
        created += raise_alert(**kw)[1]

    for v in Vehicle.objects.exclude(status=Vehicle.Status.INACTIVE):
        if v.next_maintenance_date and v.next_maintenance_date <= horizon:
            add(
                kind=Alert.Kind.MAINTENANCE,
                severity=_expiry_severity(v.next_maintenance_date, today),
                title=f"Manutenção por data: {v.plate}",
                message=f"{v.plate} tem manutenção prevista para {v.next_maintenance_date:%d/%m/%Y}.",
                dedupe_key=f"maint-date:{v.pk}:{v.next_maintenance_date}",
                vehicle=v,
            )
        if v.next_maintenance_km and v.odometer_km >= v.next_maintenance_km - settings.ALERT_KM_BEFORE_MAINTENANCE:
            overdue = v.odometer_km >= v.next_maintenance_km
            add(
                kind=Alert.Kind.MAINTENANCE,
                severity=Alert.Severity.CRITICAL if overdue else Alert.Severity.WARNING,
                title=f"Manutenção por km: {v.plate}",
                message=f"{v.plate} está com {v.odometer_km} km; revisão prevista aos {v.next_maintenance_km} km.",
                dedupe_key=f"maint-km:{v.pk}:{v.next_maintenance_km}",
                vehicle=v,
            )
        for field, label in (("insurance_expiry", "Seguro"), ("licensing_expiry", "Licenciamento")):
            day = getattr(v, field)
            if day and day <= horizon:
                state = "venceu" if day < today else "vence"
                add(
                    kind=Alert.Kind.DOCUMENT,
                    severity=_expiry_severity(day, today),
                    title=f"{label} {state}: {v.plate}",
                    message=f"{label} de {v.plate} {state} em {day:%d/%m/%Y}.",
                    dedupe_key=f"doc:vehicle:{v.pk}:{field}:{day}",
                    vehicle=v,
                )

    for d in Driver.objects.filter(is_active=True, license_expiry__lte=horizon):
        state = "venceu" if d.license_expiry < today else "vence"
        add(
            kind=Alert.Kind.DOCUMENT,
            severity=_expiry_severity(d.license_expiry, today),
            title=f"CNH {state}: {d.full_name}",
            message=f"A CNH de {d.full_name} {state} em {d.license_expiry:%d/%m/%Y}.",
            dedupe_key=f"doc:driver:{d.pk}:{d.license_expiry}",
            driver=d,
        )

    late_running = Trip.objects.filter(status=Trip.Status.IN_PROGRESS, scheduled_arrival__lt=now)
    late_start = Trip.objects.filter(status=Trip.Status.PLANNED, scheduled_start__lt=now - timedelta(minutes=30))
    for trip, msg in [(t, "passou do horário previsto de chegada") for t in late_running.select_related("vehicle")] + [
        (t, "não foi iniciada no horário previsto") for t in late_start.select_related("vehicle")
    ]:
        add(
            kind=Alert.Kind.TRIP_DELAY,
            severity=Alert.Severity.WARNING,
            title=f"Viagem atrasada: {trip.code}",
            message=f"A viagem {trip.code} ({trip.origin} → {trip.destination}) {msg}.",
            dedupe_key=f"delay:{trip.pk}:{trip.status}",
            vehicle=trip.vehicle,
            trip=trip,
        )
    return created
