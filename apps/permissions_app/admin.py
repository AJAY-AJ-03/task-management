from django.contrib import admin

from .models import PermissionRequest


@admin.register(PermissionRequest)
class PermissionRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "start_time", "end_time", "duration_minutes", "status", "approved_by")
    list_filter = ("status", "date")
    search_fields = ("employee__employee_code", "employee__user__username", "reason")
