from .models import AuditLog
from .services import diff, record, snapshot


class AuditedMixin:
    """Registra criação, alteração e exclusão feitas pela API. Use antes do ModelViewSet."""

    def get_create_kwargs(self):
        return {}

    def perform_create(self, serializer):
        instance = serializer.save(**self.get_create_kwargs())
        record(self.request, AuditLog.Action.CREATE, instance, snapshot(instance))

    def perform_update(self, serializer):
        before = snapshot(serializer.instance)
        instance = serializer.save()
        record(self.request, AuditLog.Action.UPDATE, instance, diff(before, snapshot(instance)))

    def perform_destroy(self, instance):
        object_id, object_repr, state = str(instance.pk), str(instance), snapshot(instance)
        instance.delete()  # se houver vínculo protegido, levanta antes de auditar
        record(self.request, AuditLog.Action.DELETE, instance, state, object_id=object_id, object_repr=object_repr)
