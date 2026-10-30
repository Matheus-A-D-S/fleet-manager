from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("vehicles", views.VehicleViewSet)
router.register("drivers", views.DriverViewSet)
router.register("maintenance", views.MaintenanceRecordViewSet)

urlpatterns = router.urls
