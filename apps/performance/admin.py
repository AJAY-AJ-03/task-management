from django.contrib import admin

from .models import KPI, EmployeeKPI, PerformanceRecord


@admin.register(KPI)
class KPIAdmin(admin.ModelAdmin):
    list_display = ("name", "unit", "target_type", "default_target", "is_active")
    list_filter = ("is_active", "target_type")
    search_fields = ("name", "description")


@admin.register(EmployeeKPI)
class EmployeeKPIAdmin(admin.ModelAdmin):
    list_display = ("employee", "kpi", "target", "effective_from", "effective_to")
    list_filter = ("kpi", "effective_from")
    search_fields = ("employee__employee_code", "employee__user__username")


@admin.register(PerformanceRecord)
class PerformanceRecordAdmin(admin.ModelAdmin):
    list_display = ("employee", "kpi", "date", "target_value", "actual_value", "achievement_percentage", "created_by")
    list_filter = ("kpi", "date")
    search_fields = ("employee__employee_code", "employee__user__username", "remarks")
