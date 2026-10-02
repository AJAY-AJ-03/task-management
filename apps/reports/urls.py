from django.urls import path

from .views import (
    AttendanceReportView,
    BreaksReportView,
    ContactOutcomeReportView,
    EmployeeProductivityReportView,
    LeaveReportView,
    PerformanceReportView,
    ProductivityReportView,
    TaskAllocationReportView,
    TasksReportView,
    TeamProductivityReportView,
)

urlpatterns = [
    path("reports/attendance/", AttendanceReportView.as_view(), name="reports-attendance"),
    path("reports/productivity/", ProductivityReportView.as_view(), name="reports-productivity"),
    path("reports/performance/", PerformanceReportView.as_view(), name="reports-performance"),
    path("reports/breaks/", BreaksReportView.as_view(), name="reports-breaks"),
    path("reports/tasks/", TasksReportView.as_view(), name="reports-tasks"),
    path("reports/leave/", LeaveReportView.as_view(), name="reports-leave"),
    path("reports/employee-productivity/", EmployeeProductivityReportView.as_view(), name="reports-employee-productivity"),
    path("reports/team-productivity/", TeamProductivityReportView.as_view(), name="reports-team-productivity"),
    path("reports/task-allocations/", TaskAllocationReportView.as_view(), name="reports-task-allocations"),
    path("reports/contact-outcomes/", ContactOutcomeReportView.as_view(), name="reports-contact-outcomes"),
]

