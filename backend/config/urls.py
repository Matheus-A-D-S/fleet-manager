from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", include("apps.core.urls")),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/fleet/", include("apps.fleet.urls")),
    path("api/logistics/", include("apps.logistics.urls")),
    path("api/alerts/", include("apps.alerts.urls")),
    path("api/audit/", include("apps.audit.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
