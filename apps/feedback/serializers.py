from rest_framework import serializers
from .models import Feedback, FeedbackStatus


class FeedbackSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source="employee.employee_code", read_only=True)
    employee_name = serializers.CharField(source="employee.user.display_name", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.display_name", read_only=True, default=None)

    class Meta:
        model = Feedback
        fields = [
            "id",
            "employee",
            "employee_code",
            "employee_name",
            "category",
            "subject",
            "description",
            "rating",
            "status",
            "response",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "employee",
            "employee_code",
            "employee_name",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]


class FeedbackRespondSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=FeedbackStatus.choices, default=FeedbackStatus.RESOLVED)
    response = serializers.CharField(required=True)
