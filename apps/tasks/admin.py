from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "assigned_to", "assigned_by", "priority", "status", "due_date", "completed_at")
    list_filter = ("status", "priority", "due_date")
    search_fields = ("title", "description", "assigned_to__employee_code", "assigned_to__user__username")
