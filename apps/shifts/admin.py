from django.contrib import admin

from .models import EmployeeShift, Shift


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("name", "start_time", "end_time", "break_duration_minutes", "is_overnight", "is_active")
    list_filter = ("is_active", "is_overnight")
    search_fields = ("name",)


@admin.register(EmployeeShift)
class EmployeeShiftAdmin(admin.ModelAdmin):
    list_display = ("employee", "shift", "effective_from", "effective_to", "assigned_by")
    list_filter = ("shift", "effective_from")
    search_fields = ("employee__employee_code", "employee__user__username")
