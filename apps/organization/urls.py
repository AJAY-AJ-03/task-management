from rest_framework.routers import DefaultRouter

from .views import DepartmentViewSet, ProcessViewSet, TeamViewSet

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("processes", ProcessViewSet, basename="process")
router.register("teams", TeamViewSet, basename="team")

urlpatterns = router.urls