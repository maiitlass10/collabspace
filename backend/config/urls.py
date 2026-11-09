from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # API documentation (public, read-only description of the endpoints)
    path("api/schema/", SpectacularAPIView.as_view(permission_classes=[]), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema", permission_classes=[]),
        name="api-docs",
    ),
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("documents.urls")),
]
