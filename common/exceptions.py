import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class BusinessRuleError(exceptions.APIException):
    """Raised by service modules when a business rule is violated (HTTP 400)."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Request could not be processed."
    default_code = "business_rule_violation"


def _envelope(message, errors, status_code):
    return Response(
        {"success": False, "message": message, "errors": errors}, status=status_code
    )


def custom_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, "error_dict") else exc.messages
        exc = exceptions.ValidationError(detail=detail)
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()
    elif isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, IntegrityError):
        logger.warning("IntegrityError: %s", exc)
        return _envelope(
            "The request conflicts with existing data.", {}, status.HTTP_409_CONFLICT
        )

    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled exception", exc_info=exc)
        return _envelope(
            "An unexpected error occurred.", {}, status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    code = response.status_code
    data = response.data

    if isinstance(exc, exceptions.ValidationError):
        errors = data if isinstance(data, dict) else {"non_field_errors": data}
        return _envelope("Validation failed.", errors, code)
    if isinstance(exc, exceptions.PermissionDenied):
        return _envelope("You are not authorized to perform this action.", {}, code)
    if isinstance(exc, exceptions.NotAuthenticated):
        return _envelope("Authentication credentials were not provided.", {}, code)
    if isinstance(exc, exceptions.Throttled):
        return _envelope("Too many requests. Please try again later.", {}, code)
    if isinstance(exc, exceptions.NotFound):
        return _envelope("Resource not found.", {}, code)

    if isinstance(data, dict) and "detail" in data:
        return _envelope(str(data["detail"]), {}, code)
    return _envelope("Request failed.", data if isinstance(data, dict) else {}, code)