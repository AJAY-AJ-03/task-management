import django_filters as df

from .models import Process, Team


class ProcessFilter(df.FilterSet):
    class Meta:
        model = Process
        fields = ["department", "is_active"]


class TeamFilter(df.FilterSet):
    class Meta:
        model = Team
        fields = ["department", "process", "manager", "team_leader", "is_active"]