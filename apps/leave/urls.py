from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    LeaveRequestViewSet,
    LeaveTypeViewSet,
    MyLeaveBalanceView,
    MyLeaveRequestsView,
)

router = DefaultRouter()
router.register(r"leave/types", LeaveTypeViewSet, basename="leave-type")
router.register(r"leave/requests", LeaveRequestViewSet, basename="leave-request")

urlpatterns = [
    path("leave/balance/", MyLeaveBalanceView.as_view(), name="leave-balance"),
    path("leave/requests/my/", MyLeaveRequestsView.as_view(), name="leave-requests-my"),
    path("", include(router.urls)),
]
