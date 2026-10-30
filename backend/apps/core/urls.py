from django.urls import path

from . import views

urlpatterns = [
    path("", views.live),
    path("ready/", views.ready),
]
