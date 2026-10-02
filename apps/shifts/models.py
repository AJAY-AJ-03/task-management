from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Shift(models.Model):
    name = models.CharField(max_length=100, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_duration_minutes = models.PositiveIntegerField(default=60)
    is_overnight = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time", "name"]
        indexes = [models.Index(fields=["is_active"])]

    def save(self, *args, **kwargs):
        # Auto-detect overnight shift if end_time <= start_time
        if self.start_time and self.end_time:
            self.is_overnight = self.end_time <= self.start_time
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"


class EmployeeShift(models.Model):
    employee = models.ForeignKey(
        "employees.EmployeeProfile", on_delete=models.CASCADE, related_name="assigned_shifts"
    )
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name="assignments")
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    assigned_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_employee_shifts"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_from"]
        indexes = [
            models.Index(fields=["employee", "effective_from"]),
            models.Index(fields=["effective_from", "effective_to"]),
        ]

    def clean(self):
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError({"effective_to": "effective_to date cannot be earlier than effective_from."})

        # Overlap check for active shifts of the same employee
        qs = EmployeeShift.objects.filter(employee=self.employee)
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        for existing in qs:
            ex_from = existing.effective_from
            ex_to = existing.effective_to
            new_from = self.effective_from
            new_to = self.effective_to

            # Overlap occurs if new_from <= ex_to (or ex_to is None) AND ex_from <= new_to (or new_to is None)
            overlap = (ex_to is None or new_from <= ex_to) and (new_to is None or ex_from <= new_to)
            if overlap:
                raise ValidationError({"effective_from": f"Overlapping shift assignment found ({ex_from} to {ex_to or 'Open'})."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.employee_code} - {self.shift.name} ({self.effective_from})"
