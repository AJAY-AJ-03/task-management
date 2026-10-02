from django.urls import path

from .views import AdminDashboardView, EmployeeDashboardView, TeamLeaderDashboardView

urlpatterns = [
    path("dashboard/employee/", EmployeeDashboardView.as_view(), name="dashboard-employee"),
    path("dashboard/admin/", AdminDashboardView.as_view(), name="dashboard-admin"),
    path("dashboard/team-leader/", TeamLeaderDashboardView.as_view(), name="dashboard-team-leader"),
]
