import django_filters

from .models import PermissionRequest


class PermissionRequestFilter(django_filters.FilterSet):
    employee = django_filters.NumberFilter(field_name="employee__id")
    team = django_filters.NumberFilter(field_name="employee__team__id")
    department = django_filters.NumberFilter(field_name="employee__department__id")
    start_date = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    end_date = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = PermissionRequest
        fields = ["employee", "status", "date", "team", "department", "start_date", "end_date"]
