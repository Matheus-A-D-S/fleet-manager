from django.contrib import admin

from .models import LocationPing, Trip

admin.site.register(Trip)
admin.site.register(LocationPing)
