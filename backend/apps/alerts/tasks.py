from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mass_mail
from django.utils import timezone

from . import services
from .models import Alert


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_alert_email(alert_id):
    alert = Alert.objects.filter(pk=alert_id).first()
    if not alert or alert.resolved:
        return
    recipients = list(
        get_user_model()
        .objects.filter(is_active=True, is_email_verified=True, role__in=["ADMIN", "MANAGER"])
        .values_list("email", flat=True)
    )
    if not recipients:
        return
    subject = f"[FleetTrack] {alert.get_severity_display()}: {alert.title}"
    body = f"{alert.message}\n\nTipo: {alert.get_kind_display()}\nRegistrado em: {timezone.localtime(alert.created_at):%d/%m/%Y %H:%M}\n"
    # Uma mensagem por destinatário, para ninguém ver o e-mail dos outros.
    send_mass_mail([(subject, body, None, [r]) for r in recipients])
    Alert.objects.filter(pk=alert.pk).update(email_sent_at=timezone.now())


@shared_task
def scan_fleet_task():
    return services.scan_fleet()
