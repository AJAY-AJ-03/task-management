from django.contrib import admin

from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "check_in", "check_out", "status", "late_minutes", "overtime_minutes")
    list_filter = ("status", "date")
    search_fields = ("employee__employee_code", "employee__user__username", "remarks")
