import django_filters

from .models import KPI, EmployeeKPI, PerformanceRecord


class KPIFilter(django_filters.FilterSet):
    class Meta:
        model = KPI
        fields = ["is_active", "target_type"]


class EmployeeKPIFilter(django_filters.FilterSet):
    employee = django_filters.NumberFilter(field_name="employee__id")
    kpi = django_filters.NumberFilter(field_name="kpi__id")

    class Meta:
        model = EmployeeKPI
        fields = ["employee", "kpi", "effective_from"]


class PerformanceRecordFilter(django_filters.FilterSet):
    employee = django_filters.NumberFilter(field_name="employee__id")
    kpi = django_filters.NumberFilter(field_name="kpi__id")
    team = django_filters.NumberFilter(field_name="employee__team__id")
    department = django_filters.NumberFilter(field_name="employee__department__id")
    start_date = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    end_date = django_filters.DateFilter(field_name="date", lookup_expr="lte")
    month = django_filters.NumberFilter(field_name="date__month")
    year = django_filters.NumberFilter(field_name="date__year")

    class Meta:
        model = PerformanceRecord
        fields = ["employee", "kpi", "date", "team", "department", "start_date", "end_date", "month", "year"]
