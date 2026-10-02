from django.contrib import admin

from .models import BreakRecord, BreakType


@admin.register(BreakType)
class BreakTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_minutes", "is_paid", "is_active")
    list_filter = ("is_active", "is_paid")
    search_fields = ("name",)


@admin.register(BreakRecord)
class BreakRecordAdmin(admin.ModelAdmin):
    list_display = ("employee", "break_type", "start_time", "end_time", "duration_seconds", "status")
    list_filter = ("status", "break_type")
    search_fields = ("employee__employee_code", "employee__user__username")
