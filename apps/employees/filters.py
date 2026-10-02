import django_filters as df

from .models import EmployeeProfile, EmployeeStatus


class EmployeeFilter(df.FilterSet):
    role = df.CharFilter(field_name="user__role")
    status = df.ChoiceFilter(choices=EmployeeStatus.choices)

    class Meta:
        model = EmployeeProfile
        fields = ["department", "process", "team", "role", "status"]