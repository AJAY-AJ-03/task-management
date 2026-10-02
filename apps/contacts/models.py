from django.db import models


class ContactAllocationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    NO_ANSWER = "NO_ANSWER", "No Answer"
    CALLBACK = "CALLBACK", "Callback"
    NOT_INTERESTED = "NOT_INTERESTED", "Not Interested"
    FAILED = "FAILED", "Failed"


class ContactImport(models.Model):
    file_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="contact_imports"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    total_rows = models.PositiveIntegerField(default=0)
    success_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    validation_errors = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.file_name} ({self.success_rows}/{self.total_rows} imported)"


class Contact(models.Model):
    contact_import = models.ForeignKey(
        ContactImport, on_delete=models.SET_NULL, null=True, blank=True, related_name="contacts"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    company = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone})".strip()


class ContactAllocation(models.Model):
    task = models.ForeignKey("tasks.Task", on_delete=models.CASCADE, related_name="allocations")
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="allocations")
    employee = models.ForeignKey(
        "employees.EmployeeProfile", on_delete=models.CASCADE, related_name="contact_allocations"
    )
    allocated_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="allocated_contacts"
    )
    allocated_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=30, choices=ContactAllocationStatus.choices, default=ContactAllocationStatus.PENDING
    )
    description = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    updated_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_contact_allocations"
    )
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-allocated_at"]
        indexes = [
            models.Index(fields=["employee", "status"]),
            models.Index(fields=["task", "status"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["deadline"]),
        ]

    def __str__(self):
        return f"{self.contact.phone} -> {self.employee.employee_code} ({self.status})"
