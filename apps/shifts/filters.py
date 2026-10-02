import django_filters

from .models import EmployeeShift, Shift


class ShiftFilter(django_filters.FilterSet):
    class Meta:
        model = Shift
        fields = ["is_active", "is_overnight"]


class EmployeeShiftFilter(django_filters.FilterSet):
    employee = django_filters.NumberFilter(field_name="employee__id")
    shift = django_filters.NumberFilter(field_name="shift__id")
    team = django_filters.NumberFilter(field_name="employee__team__id")
    department = django_filters.NumberFilter(field_name="employee__department__id")
    active_on = django_filters.DateFilter(method="filter_active_on")

    class Meta:
        model = EmployeeShift
        fields = ["employee", "shift", "team", "department", "effective_from", "effective_to"]

    def filter_active_on(self, queryset, name, value):
        return queryset.filter(
            effective_from__lte=value
        ).filter(
            django_filters.db_models.Q(effective_to__isnull=True) | django_filters.db_models.Q(effective_to__gte=value)
        )
