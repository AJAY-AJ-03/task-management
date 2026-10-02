import django_filters
from .models import SOP


class SOPFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr="icontains")
    category = django_filters.CharFilter(lookup_expr="iexact")
    status = django_filters.CharFilter(lookup_expr="iexact")
    department = django_filters.NumberFilter(field_name="department_id")
    process = django_filters.NumberFilter(field_name="process_id")
    team = django_filters.NumberFilter(field_name="team_id")

    class Meta:
        model = SOP
        fields = ["title", "category", "status", "department", "process", "team"]
