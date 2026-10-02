from django.db import models

from common.validators import validate_phone


class EmployeeStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    ON_NOTICE = "ON_NOTICE", "On Notice"
    TERMINATED = "TERMINATED", "Terminated"


def profile_image_path(instance, filename):
    return f"employee_profiles/{instance.employee_code}/{filename}"


class EmployeeProfile(models.Model):
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="employee_profile")
    employee_code = models.CharField(max_length=50, unique=True)
    date_of_joining = models.DateField()
    designation = models.CharField(max_length=100)
    department = models.ForeignKey("organization.Department", on_delete=models.PROTECT, related_name="employees")
    process = models.ForeignKey("organization.Process", on_delete=models.PROTECT, related_name="employees")
    team = models.ForeignKey("organization.Team", on_delete=models.PROTECT, related_name="employees")
    reporting_manager = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="direct_reports"
    )
    team_leader = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="led_employees"
    )
    phone = models.CharField(max_length=20, blank=True, validators=[validate_phone])
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, validators=[validate_phone])
    profile_image = models.ImageField(upload_to=profile_image_path, null=True, blank=True)
    status = models.CharField(max_length=20, choices=EmployeeStatus.choices, default=EmployeeStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["employee_code"]
        indexes = [
            models.Index(fields=["department"]),
            models.Index(fields=["process"]),
            models.Index(fields=["team"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.employee_code} - {self.user.display_name}"