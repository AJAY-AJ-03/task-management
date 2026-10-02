import django_filters
from .models import Escalation


class EscalationFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(lookup_expr="iexact")
    priority = django_filters.CharFilter(lookup_expr="iexact")
    raised_by = django_filters.NumberFilter(field_name="raised_by_id")

    class Meta:
        model = Escalation
        fields = ["status", "priority", "raised_by"]
