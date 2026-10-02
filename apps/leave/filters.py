import django_filters

from .models import LeaveBalance, LeaveRequest, LeaveType


class LeaveTypeFilter(django_filters.FilterSet):
    class Meta:
        model = LeaveType
        fields = ["is_active"]


class LeaveBalanceFilter(django_filters.FilterSet):
    employee = django_filters.NumberFilter(field_name="employee__id")
    leave_type = django_filters.NumberFilter(field_name="leave_type__id")
    year = django_filters.NumberFilter(field_name="year")

    class Meta:
        model = LeaveBalance
        fields = ["employee", "leave_type", "year"]


class LeaveRequestFilter(django_filters.FilterSet):
    employee = django_filters.NumberFilter(field_name="employee__id")
    leave_type = django_filters.NumberFilter(field_name="leave_type__id")
    team = django_filters.NumberFilter(field_name="employee__team__id")
    department = django_filters.NumberFilter(field_name="employee__department__id")
    start_date = django_filters.DateFilter(field_name="start_date", lookup_expr="gte")
    end_date = django_filters.DateFilter(field_name="end_date", lookup_expr="lte")

    class Meta:
        model = LeaveRequest
        fields = ["employee", "leave_type", "status", "team", "department", "start_date", "end_date"]
