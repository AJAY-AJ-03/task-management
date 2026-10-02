from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AttendanceViewSet,
    CheckInView,
    CheckOutView,
    MonthlyAttendanceView,
    MyAttendanceView,
    MyTodayAttendanceView,
    TeamAttendanceView,
)

router = DefaultRouter()
router.register(r"attendance", AttendanceViewSet, basename="attendance")

urlpatterns = [
    path("attendance/check-in/", CheckInView.as_view(), name="attendance-check-in"),
    path("attendance/check-out/", CheckOutView.as_view(), name="attendance-check-out"),
    path("attendance/my/", MyAttendanceView.as_view(), name="attendance-my"),
    path("attendance/my/today/", MyTodayAttendanceView.as_view(), name="attendance-my-today"),
    path("attendance/team/", TeamAttendanceView.as_view(), name="attendance-team"),
    path("attendance/monthly/", MonthlyAttendanceView.as_view(), name="attendance-monthly"),
    path("", include(router.urls)),
]
