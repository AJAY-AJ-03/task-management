from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DailyPerformanceReportView,
    EmployeeKPIViewSet,
    KPIViewSet,
    MonthlyPerformanceReportView,
    MyKPIsView,
    MyPerformanceView,
    PerformanceRecordViewSet,
    TeamPerformanceReportView,
)

router = DefaultRouter()
router.register(r"kpis", KPIViewSet, basename="kpi")
router.register(r"employee-kpis", EmployeeKPIViewSet, basename="employee-kpi")
router.register(r"performance", PerformanceRecordViewSet, basename="performance")

urlpatterns = [
    path("kpis/my/", MyKPIsView.as_view(), name="kpis-my"),
    path("performance/my/", MyPerformanceView.as_view(), name="performance-my"),
    path("performance/daily/", DailyPerformanceReportView.as_view(), name="performance-daily"),
    path("performance/team/", TeamPerformanceReportView.as_view(), name="performance-team"),
    path("performance/monthly/", MonthlyPerformanceReportView.as_view(), name="performance-monthly"),
    path("", include(router.urls)),
]
