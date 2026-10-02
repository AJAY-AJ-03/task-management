from django.db import models


class FeedbackStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted"
    REVIEWED = "REVIEWED", "Reviewed"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"


class Feedback(models.Model):
    employee = models.ForeignKey(
        "employees.EmployeeProfile", on_delete=models.CASCADE, related_name="feedback_submissions"
    )
    category = models.CharField(max_length=100, default="General")
    subject = models.CharField(max_length=200)
    description = models.TextField()
    rating = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=FeedbackStatus.choices, default=FeedbackStatus.SUBMITTED)
    response = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_feedback"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employee", "status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return f"{self.subject} ({self.status})"
