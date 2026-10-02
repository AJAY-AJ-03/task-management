from rest_framework.routers import DefaultRouter
from .views import EscalationViewSet

router = DefaultRouter()
router.register("escalations", EscalationViewSet, basename="escalation")

urlpatterns = router.urls
