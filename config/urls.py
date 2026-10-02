from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    # Add one include per app as phases are built, e.g.:
    # path("api/", include("apps.organization.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/", include("apps.organization.urls")),
    path("api/", include("apps.employees.urls")),
    path("api/", include("apps.shifts.urls")),
    path("api/", include("apps.attendance.urls")),
    path("api/", include("apps.breaks.urls")),
    path("api/", include("apps.tasks.urls")),
    path("api/", include("apps.performance.urls")),
    path("api/", include("apps.leave.urls")),
    path("api/", include("apps.permissions_app.urls")),
    path("api/", include("apps.dashboards.urls")),
    path("api/", include("apps.reports.urls")),
    path("api/", include("apps.sop.urls")),
    path("api/", include("apps.escalations.urls")),
    path("api/", include("apps.feedback.urls")),
    path("api/", include("apps.contacts.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)