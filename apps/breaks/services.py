from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.attendance.models import Attendance
from common.exceptions import BusinessRuleError

from .models import BreakRecord, BreakStatus, BreakType


@transaction.atomic
def start_break(employee, break_type_id, start_time=None):
    start_time = start_time or timezone.now()
    date_val = timezone.localdate(start_time)

    active_break = BreakRecord.objects.filter(employee=employee, status=BreakStatus.ACTIVE).first()
    if active_break:
        raise BusinessRuleError("Employee already has an active break in progress.")

    break_type = BreakType.objects.filter(pk=break_type_id, is_active=True).first()
    if not break_type:
        raise BusinessRuleError("Invalid or inactive break type.")

    attendance = Attendance.objects.filter(employee=employee, date=date_val).first()

    return BreakRecord.objects.create(
        employee=employee,
        break_type=break_type,
        attendance=attendance,
        start_time=start_time,
        status=BreakStatus.ACTIVE,
    )


@transaction.atomic
def end_break(employee, end_time=None):
    end_time = end_time or timezone.now()

    active_break = BreakRecord.objects.filter(employee=employee, status=BreakStatus.ACTIVE).first()
    if not active_break:
        raise BusinessRuleError("No active break found to end.")

    if end_time < active_break.start_time:
        raise BusinessRuleError("End time cannot be earlier than start time.")

    active_break.end_time = end_time
    active_break.status = BreakStatus.COMPLETED
    active_break.save()
    return active_break


def calculate_daily_break_duration(employee, date_val):
    result = (
        BreakRecord.objects.filter(
            employee=employee,
            start_time__date=date_val,
            status=BreakStatus.COMPLETED,
        ).aggregate(total=Sum("duration_seconds"))
    )
    return result["total"] or 0
