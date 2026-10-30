from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "severity", "resolved", "email_sent_at", "created_at")
    list_filter = ("kind", "severity", "resolved")
