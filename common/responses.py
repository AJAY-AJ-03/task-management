from drf_spectacular.utils import inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response


def success_response(data=None, message="Success.", status_code=status.HTTP_200_OK):
    return Response(
        {"success": True, "message": message, "data": {} if data is None else data},
        status=status_code,
    )


def error_response(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {"success": False, "message": message, "errors": errors or {}},
        status=status_code,
    )


def envelope(name, data=None, many=False):
    """OpenAPI schema helper describing the standard success envelope."""
    data_field = data or serializers.DictField()
    if data is not None and many:
        data_field = data.__class__(many=True)
    return inline_serializer(
        name=name,
        fields={
            "success": serializers.BooleanField(default=True),
            "message": serializers.CharField(),
            "data": data_field,
        },
    )


class ErrorEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    message = serializers.CharField()
    errors = serializers.DictField()