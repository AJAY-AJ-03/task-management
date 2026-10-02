from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ActiveBreaksView,
    BreakRecordViewSet,
    BreakTypeViewSet,
    DailyBreakSummaryView,
    EndBreakView,
    MyBreaksView,
    MyTodayBreaksView,
    StartBreakView,
    TeamBreaksView,
)

router = DefaultRouter()
router.register(r"break-types", BreakTypeViewSet, basename="break-type")
router.register(r"breaks", BreakRecordViewSet, basename="break-record")

urlpatterns = [
    path("breaks/start/", StartBreakView.as_view(), name="breaks-start"),
    path("breaks/end/", EndBreakView.as_view(), name="breaks-end"),
    path("breaks/my/", MyBreaksView.as_view(), name="breaks-my"),
    path("breaks/my/today/", MyTodayBreaksView.as_view(), name="breaks-my-today"),
    path("breaks/active/", ActiveBreaksView.as_view(), name="breaks-active"),
    path("breaks/team/", TeamBreaksView.as_view(), name="breaks-team"),
    path("breaks/daily-summary/", DailyBreakSummaryView.as_view(), name="breaks-daily-summary"),
    path("", include(router.urls)),
]
