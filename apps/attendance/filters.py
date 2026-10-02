import django_filters

from .models import Attendance


class AttendanceFilter(django_filters.FilterSet):
    employee = django_filters.NumberFilter(field_name="employee__id")
    team = django_filters.NumberFilter(field_name="employee__team__id")
    department = django_filters.NumberFilter(field_name="employee__department__id")
    start_date = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    end_date = django_filters.DateFilter(field_name="date", lookup_expr="lte")
    month = django_filters.NumberFilter(field_name="date__month")
    year = django_filters.NumberFilter(field_name="date__year")

    class Meta:
        model = Attendance
        fields = ["employee", "date", "status", "team", "department", "start_date", "end_date", "month", "year"]
