from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("trips", views.TripViewSet, basename="trip")
router.register("pings", views.PingViewSet, basename="ping")

urlpatterns = [
    path("live/", views.LiveFleetView.as_view()),
    path("dashboard/", views.DashboardView.as_view()),
] + router.urls
