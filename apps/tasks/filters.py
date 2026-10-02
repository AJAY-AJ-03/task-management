import django_filters

from .models import Task


class TaskFilter(django_filters.FilterSet):
    employee = django_filters.NumberFilter(field_name="assigned_to__id")
    team = django_filters.NumberFilter(field_name="team__id")
    due_date = django_filters.DateFilter(field_name="due_date")
    due_before = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")
    due_after = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")

    class Meta:
        model = Task
        fields = ["status", "priority", "employee", "team", "due_date", "due_before", "due_after"]
