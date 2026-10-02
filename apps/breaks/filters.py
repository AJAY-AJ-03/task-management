import django_filters

from .models import BreakRecord, BreakType


class BreakTypeFilter(django_filters.FilterSet):
    class Meta:
        model = BreakType
        fields = ["is_active", "is_paid"]


class BreakRecordFilter(django_filters.FilterSet):
    employee = django_filters.NumberFilter(field_name="employee__id")
    break_type = django_filters.NumberFilter(field_name="break_type__id")
    team = django_filters.NumberFilter(field_name="employee__team__id")
    department = django_filters.NumberFilter(field_name="employee__department__id")
    date = django_filters.DateFilter(field_name="start_time__date")
    start_date = django_filters.DateFilter(field_name="start_time__date", lookup_expr="gte")
    end_date = django_filters.DateFilter(field_name="start_time__date", lookup_expr="lte")

    class Meta:
        model = BreakRecord
        fields = ["employee", "break_type", "status", "team", "department", "date", "start_date", "end_date"]
