from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MyPermissionsView, PermissionRequestViewSet

router = DefaultRouter()
router.register(r"permissions", PermissionRequestViewSet, basename="permission")

urlpatterns = [
    path("permissions/my/", MyPermissionsView.as_view(), name="permissions-my"),
    path("", include(router.urls)),
]
