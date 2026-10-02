from rest_framework.permissions import BasePermission

ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_MANAGER = "MANAGER"
ROLE_TEAM_LEADER = "TEAM_LEADER"
ROLE_EMPLOYEE = "EMPLOYEE"


class RolePermission(BasePermission):
    allowed_roles: tuple = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role in self.allowed_roles
        )


class IsSuperAdmin(RolePermission):
    allowed_roles = (ROLE_SUPER_ADMIN,)


class IsManager(RolePermission):
    allowed_roles = (ROLE_MANAGER,)


class IsTeamLeader(RolePermission):
    allowed_roles = (ROLE_TEAM_LEADER,)


class IsEmployee(RolePermission):
    allowed_roles = (ROLE_EMPLOYEE,)


class IsAdminOrManager(RolePermission):
    allowed_roles = (ROLE_SUPER_ADMIN, ROLE_MANAGER)


class IsManagerOrTeamLeader(RolePermission):
    """Super admin is included because that role has full access."""

    allowed_roles = (ROLE_SUPER_ADMIN, ROLE_MANAGER, ROLE_TEAM_LEADER)


def _owner_user_id(obj):
    """Resolve the owning User id for User, EmployeeProfile or employee-linked objects."""
    if hasattr(obj, "role") and hasattr(obj, "username"):  # a User
        return obj.pk
    if hasattr(obj, "user_id"):  # EmployeeProfile
        return obj.user_id
    employee = getattr(obj, "employee", None)  # Attendance, Task, LeaveRequest ...
    if employee is not None:
        return getattr(employee, "user_id", None)
    return None


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        owner_id = _owner_user_id(obj)
        return owner_id is not None and owner_id == request.user.pk


def _team_id_of(obj):
    if obj.__class__.__name__ == "Team":
        return obj.pk
    if hasattr(obj, "team_id"):
        return obj.team_id
    employee = getattr(obj, "employee", None)
    return getattr(employee, "team_id", None)


class IsTeamMember(BasePermission):
    """
    Object-level: the object's team is one the user leads, manages or belongs to.
    Super admin always passes. Requires apps.organization (Phase 2).
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == ROLE_SUPER_ADMIN:
            return True
        team_id = _team_id_of(obj)
        if team_id is None:
            return False

        from apps.organization.models import Team

        if Team.objects.filter(pk=team_id).filter(
            models_q_manager_or_leader(user)
        ).exists():
            return True
        profile = getattr(user, "employee_profile", None)
        return bool(profile and profile.team_id == team_id)


def models_q_manager_or_leader(user):
    from django.db.models import Q

    return Q(manager=user) | Q(team_leader=user)


def is_employee_in_actor_scope(actor, employee):
    if not actor or not actor.is_authenticated:
        return False
    if actor.role == ROLE_SUPER_ADMIN:
        return True
    if not employee:
        return False
    if actor.role == ROLE_MANAGER:
        return (
            employee.reporting_manager_id == actor.pk
            or (employee.team_id is not None and employee.team.manager_id == actor.pk)
        )
    if actor.role == ROLE_TEAM_LEADER:
        return (
            employee.team_leader_id == actor.pk
            or (employee.team_id is not None and employee.team.team_leader_id == actor.pk)
        )
    if actor.role == ROLE_EMPLOYEE:
        return employee.user_id == actor.pk
    return False


def get_employee_scoped_queryset(user, queryset=None):
    from django.db.models import Q
    if queryset is None:
        from apps.employees.models import EmployeeProfile
        queryset = EmployeeProfile.objects.all()
    if not user or not user.is_authenticated:
        return queryset.none()
    if user.role == ROLE_SUPER_ADMIN:
        return queryset
    if user.role == ROLE_MANAGER:
        return queryset.filter(
            Q(reporting_manager=user) | Q(team__manager=user)
        ).distinct()
    if user.role == ROLE_TEAM_LEADER:
        return queryset.filter(
            Q(team_leader=user) | Q(team__team_leader=user)
        ).distinct()
    if user.role == ROLE_EMPLOYEE:
        return queryset.filter(user=user)
    return queryset.none()


def get_scoped_queryset(user, queryset, employee_field="employee"):
    from django.db.models import Q
    if not user or not user.is_authenticated:
        return queryset.none()
    if user.role == ROLE_SUPER_ADMIN:
        return queryset
    if user.role == ROLE_MANAGER:
        return queryset.filter(
            Q(**{f"{employee_field}__reporting_manager": user})
            | Q(**{f"{employee_field}__team__manager": user})
        ).distinct()
    if user.role == ROLE_TEAM_LEADER:
        return queryset.filter(
            Q(**{f"{employee_field}__team_leader": user})
            | Q(**{f"{employee_field}__team__team_leader": user})
        ).distinct()
    if user.role == ROLE_EMPLOYEE:
        return queryset.filter(**{f"{employee_field}__user": user})
    return queryset.none()


def get_task_scoped_queryset(user, queryset=None):
    from django.db.models import Q
    if queryset is None:
        from apps.tasks.models import Task
        queryset = Task.objects.all()
    if not user or not user.is_authenticated:
        return queryset.none()
    if user.role == ROLE_SUPER_ADMIN:
        return queryset
    if user.role == ROLE_MANAGER:
        return queryset.filter(
            Q(assigned_to__reporting_manager=user)
            | Q(assigned_to__team__manager=user)
            | Q(team__manager=user)
            | Q(assigned_by=user)
        ).distinct()
    if user.role == ROLE_TEAM_LEADER:
        return queryset.filter(
            Q(assigned_to__team_leader=user)
            | Q(assigned_to__team__team_leader=user)
            | Q(team__team_leader=user)
            | Q(assigned_by=user)
        ).distinct()
    if user.role == ROLE_EMPLOYEE:
        profile = getattr(user, "employee_profile", None)
        return queryset.filter(assigned_to=profile) if profile else queryset.none()
    return queryset.none()


def get_team_scoped_queryset(user, queryset=None):
    from django.db.models import Q
    if queryset is None:
        from apps.organization.models import Team
        queryset = Team.objects.all()
    if not user or not user.is_authenticated:
        return queryset.none()
    if user.role == ROLE_SUPER_ADMIN:
        return queryset
    if user.role == ROLE_MANAGER:
        return queryset.filter(
            Q(manager=user) | Q(employees__reporting_manager=user)
        ).distinct()
    if user.role == ROLE_TEAM_LEADER:
        return queryset.filter(
            Q(team_leader=user) | Q(employees__team_leader=user)
        ).distinct()
    if user.role == ROLE_EMPLOYEE:
        profile = getattr(user, "employee_profile", None)
        return queryset.filter(employees=profile).distinct() if profile else queryset.none()
    return queryset.none()
