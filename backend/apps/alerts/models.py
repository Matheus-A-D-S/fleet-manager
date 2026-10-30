from django.db import models


class Alert(models.Model):
    class Kind(models.TextChoices):
        MAINTENANCE = "MAINTENANCE", "Manutenção"
        DOCUMENT = "DOCUMENT", "Documento a vencer"
        SPEEDING = "SPEEDING", "Excesso de velocidade"
        TRIP_DELAY = "TRIP_DELAY", "Viagem atrasada"

    class Severity(models.TextChoices):
        INFO = "INFO", "Informativo"
        WARNING = "WARNING", "Atenção"
        CRITICAL = "CRITICAL", "Crítico"

    kind = models.CharField(max_length=12, choices=Kind.choices, db_index=True)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.WARNING)
    title = models.CharField(max_length=160)
    message = models.TextField()
    vehicle = models.ForeignKey("fleet.Vehicle", null=True, blank=True, on_delete=models.CASCADE)
    driver = models.ForeignKey("fleet.Driver", null=True, blank=True, on_delete=models.CASCADE)
    trip = models.ForeignKey("logistics.Trip", null=True, blank=True, on_delete=models.CASCADE)
    # A chave embute o que torna o problema único (ex.: data de vencimento), então renovar o
    # documento gera uma chave nova; já um alerta resolvido não é recriado pela próxima varredura.
    dedupe_key = models.CharField(max_length=120)
    resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["dedupe_key"], name="uniq_alert_dedupe_key")]

    def __str__(self):
        return f"[{self.severity}] {self.title}"
