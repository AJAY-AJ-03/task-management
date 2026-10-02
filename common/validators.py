import re

from django.core.exceptions import ValidationError

PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")


def validate_phone(value):
    if value and not PHONE_RE.match(value):
        raise ValidationError("Enter a valid phone number (7-15 digits, optional +).")


def validate_positive(value):
    if value is not None and value <= 0:
        raise ValidationError("Value must be greater than zero.")


def validate_date_range(start, end, start_name="start_date", end_name="end_date"):
    if start and end and start > end:
        raise ValidationError({end_name: f"{end_name} cannot be before {start_name}."})


def validate_time_range(start, end, allow_overnight=False, end_name="end_time"):
    if start and end and end <= start and not allow_overnight:
        raise ValidationError({end_name: "End time must be after start time."})