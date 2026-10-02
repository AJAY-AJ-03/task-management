import datetime
from django.db import transaction
from django.utils import timezone

from apps.shifts.models import EmployeeShift
from common.exceptions import BusinessRuleError

from .models import Attendance, AttendanceStatus


def get_active_shift_for_employee(employee, date_val):
    return (
        EmployeeShift.objects.filter(employee=employee, effective_from__lte=date_val)
        .filter(models_q_open_or_future(date_val))
        .select_related("shift")
        .order_by("-effective_from")
        .first()
    )


def models_q_open_or_future(date_val):
    from django.db.models import Q
    return Q(effective_to__isnull=True) | Q(effective_to__gte=date_val)


def calculate_late_minutes(shift, check_in_dt):
    if not shift or not check_in_dt:
        return 0
    date_val = timezone.localdate(check_in_dt)
    shift_start_dt = timezone.make_aware(
        datetime.datetime.combine(date_val, shift.start_time), timezone.get_current_timezone()
    )
    if check_in_dt > shift_start_dt:
        diff = check_in_dt - shift_start_dt
        return int(diff.total_seconds() // 60)
    return 0


def calculate_overtime_minutes(shift, check_in_dt, check_out_dt):
    if not shift or not check_in_dt or not check_out_dt:
        return 0
    date_val = timezone.localdate(check_in_dt)
    shift_end = shift.end_time
    # If shift is overnight, end time lands on next day
    if shift.is_overnight:
        end_date = date_val + datetime.timedelta(days=1)
    else:
        end_date = date_val

    shift_end_dt = timezone.make_aware(
        datetime.datetime.combine(end_date, shift_end), timezone.get_current_timezone()
    )

    if check_out_dt > shift_end_dt:
        diff = check_out_dt - shift_end_dt
        return int(diff.total_seconds() // 60)
    return 0


@transaction.atomic
def check_in_employee(employee, check_in_dt=None, remarks=""):
    check_in_dt = check_in_dt or timezone.now()
    date_val = timezone.localdate(check_in_dt)

    attendance, created = Attendance.objects.get_or_create(
        employee=employee,
        date=date_val,
        defaults={"status": AttendanceStatus.PRESENT, "remarks": remarks},
    )

    if not created and attendance.check_in is not None:
        raise BusinessRuleError("Employee has already checked in for today.")

    emp_shift = get_active_shift_for_employee(employee, date_val)
    shift = emp_shift.shift if emp_shift else None

    late = calculate_late_minutes(shift, check_in_dt)

    attendance.check_in = check_in_dt
    attendance.status = AttendanceStatus.PRESENT
    attendance.late_minutes = late
    if remarks:
        attendance.remarks = remarks
    attendance.save()
    return attendance


@transaction.atomic
def check_out_employee(employee, check_out_dt=None):
    check_out_dt = check_out_dt or timezone.now()
    date_val = timezone.localdate(check_out_dt)

    attendance = Attendance.objects.filter(employee=employee, date=date_val).first()
    if not attendance or not attendance.check_in:
        # Check previous day for overnight shifts
        prev_date = date_val - datetime.timedelta(days=1)
        prev_attendance = Attendance.objects.filter(
            employee=employee, date=prev_date, check_out__isnull=True
        ).first()
        if prev_attendance and prev_attendance.check_in:
            attendance = prev_attendance

    if not attendance or not attendance.check_in:
        raise BusinessRuleError("Cannot check out without an active check-in record.")

    if attendance.check_out is not None:
        raise BusinessRuleError("Employee has already checked out for this shift.")

    if check_out_dt < attendance.check_in:
        raise BusinessRuleError("Check-out time cannot be earlier than check-in time.")

    emp_shift = get_active_shift_for_employee(employee, attendance.date)
    shift = emp_shift.shift if emp_shift else None

    overtime = calculate_overtime_minutes(shift, attendance.check_in, check_out_dt)

    attendance.check_out = check_out_dt
    attendance.overtime_minutes = overtime
    attendance.save()
    return attendance
