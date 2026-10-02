from django.contrib import admin

from .models import EmployeeProfile


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("employee_code", "user", "designation", "department", "team", "status")
    list_filter = ("department", "team", "status")
    search_fields = ("employee_code", "user__username", "user__email")
    autocomplete_fields = ("user", "department", "process", "team", "reporting_manager", "team_leader")