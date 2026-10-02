import django_filters
from .models import Feedback


class FeedbackFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(lookup_expr="iexact")
    status = django_filters.CharFilter(lookup_expr="iexact")
    employee = django_filters.NumberFilter(field_name="employee_id")

    class Meta:
        model = Feedback
        fields = ["category", "status", "employee"]
