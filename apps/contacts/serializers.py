from rest_framework import serializers
from .models import (
    Contact,
    ContactAllocation,
    ContactAllocationStatus,
    ContactImport,
)


class ContactImportSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.display_name", read_only=True, default=None)

    class Meta:
        model = ContactImport
        fields = [
            "id",
            "file_name",
            "uploaded_by",
            "uploaded_by_name",
            "uploaded_at",
            "total_rows",
            "success_rows",
            "failed_rows",
            "validation_errors",
        ]
        read_only_fields = fields


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            "id",
            "contact_import",
            "first_name",
            "last_name",
            "phone",
            "email",
            "company",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ContactAllocationSerializer(serializers.ModelSerializer):
    contact_details = ContactSerializer(source="contact", read_only=True)
    employee_code = serializers.CharField(source="employee.employee_code", read_only=True)
    employee_name = serializers.CharField(source="employee.user.display_name", read_only=True)
    allocated_by_name = serializers.CharField(source="allocated_by.display_name", read_only=True, default=None)
    updated_by_name = serializers.CharField(source="updated_by.display_name", read_only=True, default=None)

    class Meta:
        model = ContactAllocation
        fields = [
            "id",
            "task",
            "contact",
            "contact_details",
            "employee",
            "employee_code",
            "employee_name",
            "allocated_by",
            "allocated_by_name",
            "allocated_at",
            "deadline",
            "status",
            "description",
            "follow_up_date",
            "updated_by",
            "updated_by_name",
            "updated_at",
            "is_active",
        ]
        read_only_fields = fields


class ExcelUploadSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="Excel file (.xlsx)")


class AllocateContactsSerializer(serializers.Serializer):
    contact_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)
    employee_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)
    title = serializers.CharField(max_length=200, default="Daily Contact Allocation Task")
    deadline = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ContactAllocationStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ContactAllocationStatus.choices)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    follow_up_date = serializers.DateField(required=False, allow_null=True)


class ContactReassignSerializer(serializers.Serializer):
    new_employee_id = serializers.IntegerField(help_text="ID of new EmployeeProfile")
    reason = serializers.CharField(required=False, allow_blank=True, default="")
