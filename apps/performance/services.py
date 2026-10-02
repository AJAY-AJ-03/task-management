from decimal import Decimal
from django.db import transaction

from apps.employees.models import EmployeeProfile
from common.exceptions import BusinessRuleError

from .models import KPI, EmployeeKPI, PerformanceRecord


def calculate_achievement(target_val, actual_val):
    target_val = Decimal(str(target_val)) if target_val is not None else Decimal("0.00")
    actual_val = Decimal(str(actual_val)) if actual_val is not None else Decimal("0.00")

    if target_val > Decimal("0.00"):
        return round((actual_val / target_val) * Decimal("100.00"), 2)
    return Decimal("0.00")


@transaction.atomic
def record_daily_performance(employee_id, kpi_id, date_val, actual_value, target_value=None, remarks="", created_by=None):
    employee = EmployeeProfile.objects.filter(pk=employee_id).first()
    if not employee:
        raise BusinessRuleError("Employee profile not found.")

    kpi = KPI.objects.filter(pk=kpi_id, is_active=True).first()
    if not kpi:
        raise BusinessRuleError("KPI not found or inactive.")

    if target_value is None:
        emp_target = (
            EmployeeKPI.objects.filter(employee=employee, kpi=kpi, effective_from__lte=date_val)
            .filter(models_q_open_or_future(date_val))
            .order_by("-effective_from")
            .first()
        )
        target_value = emp_target.target if emp_target else kpi.default_target

    target_dec = Decimal(str(target_value))
    actual_dec = Decimal(str(actual_value))
    achievement = calculate_achievement(target_dec, actual_dec)

    record, _ = PerformanceRecord.objects.update_or_create(
        employee=employee,
        kpi=kpi,
        date=date_val,
        defaults={
            "target_value": target_dec,
            "actual_value": actual_dec,
            "achievement_percentage": achievement,
            "remarks": remarks,
            "created_by": created_by,
        },
    )
    return record


def models_q_open_or_future(date_val):
    from django.db.models import Q
    return Q(effective_to__isnull=True) | Q(effective_to__gte=date_val)
