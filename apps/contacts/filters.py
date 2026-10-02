import django_filters
from .models import Contact, ContactAllocation


class ContactFilter(django_filters.FilterSet):
    first_name = django_filters.CharFilter(lookup_expr="icontains")
    phone = django_filters.CharFilter(lookup_expr="icontains")
    email = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Contact
        fields = ["first_name", "phone", "email"]


class ContactAllocationFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(lookup_expr="iexact")
    task = django_filters.NumberFilter(field_name="task_id")
    employee = django_filters.NumberFilter(field_name="employee_id")
    is_active = django_filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = ContactAllocation
        fields = ["status", "task", "employee", "is_active"]
