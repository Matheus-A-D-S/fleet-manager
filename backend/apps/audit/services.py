import ipaddress
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict

from apps.core.logging import request_id_var

from .models import AuditLog


def snapshot(instance):
    """Estado editável do objeto, em tipos JSON."""
    return json.loads(json.dumps(model_to_dict(instance), cls=DjangoJSONEncoder))


def diff(before, after):
    return {k: {"from": before.get(k), "to": v} for k, v in after.items() if before.get(k) != v}


def _client_ip(request):
    # Atrás do Nginx o X-Forwarded-For é confiável; fora dele pode ser forjado.
    raw = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return None


def record(request, action, instance, changes=None, *, object_id=None, object_repr=None):
    user = request.user if request.user.is_authenticated else None
    return AuditLog.objects.create(
        user=user,
        user_email=getattr(user, "email", ""),
        action=action,
        model=instance._meta.label,
        object_id=object_id or str(instance.pk),
        object_repr=(object_repr or str(instance))[:200],
        changes=changes or {},
        ip_address=_client_ip(request),
        request_id=request_id_var.get() if request_id_var.get() != "-" else "",
    )
