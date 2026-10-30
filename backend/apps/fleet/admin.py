from django.contrib import admin

from .models import Driver, MaintenanceRecord, Vehicle

admin.site.register(Vehicle)
admin.site.register(Driver)
admin.site.register(MaintenanceRecord)
