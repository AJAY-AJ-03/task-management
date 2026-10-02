from django.contrib import admin

from .models import LeaveBalance, LeaveRequest, LeaveType


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "default_days", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "year", "allocated_days", "used_days", "remaining_days")
    list_filter = ("leave_type", "year")
    search_fields = ("employee__employee_code", "employee__user__username")


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "start_date", "end_date", "total_days", "status", "approved_by")
    list_filter = ("status", "leave_type", "start_date")
    search_fields = ("employee__employee_code", "employee__user__username", "reason")
