from rest_framework.routers import DefaultRouter
from .views import SOPViewSet

router = DefaultRouter()
router.register("sops", SOPViewSet, basename="sop")

urlpatterns = router.urls
