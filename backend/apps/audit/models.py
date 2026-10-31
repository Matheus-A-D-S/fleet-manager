from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Trilha de auditoria: quem fez o quê, quando e de onde."""

    class Action(models.TextChoices):
        CREATE = "CREATE", "Criação"
        UPDATE = "UPDATE", "Alteração"
        DELETE = "DELETE", "Exclusão"
        ACTION = "ACTION", "Ação"

    organization = models.ForeignKey("accounts.Organization", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    user_email = models.CharField(max_length=254, blank=True)  # mantém a identificação mesmo se o usuário for apagado
    action = models.CharField(max_length=8, choices=Action.choices)
    model = models.CharField(max_length=80)
    object_id = models.CharField(max_length=40)
    object_repr = models.CharField(max_length=200)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    request_id = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["model", "object_id"])]

    def __str__(self):
        return f"{self.action} {self.model}#{self.object_id} por {self.user_email or '-'}"
