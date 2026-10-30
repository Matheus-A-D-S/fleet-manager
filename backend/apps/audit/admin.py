from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user_email", "action", "model", "object_repr")
    list_filter = ("action", "model")
    search_fields = ("user_email", "object_repr")

    # trilha imutável: ninguém edita ou apaga pelo admin
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
