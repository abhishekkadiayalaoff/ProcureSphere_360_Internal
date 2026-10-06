from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler returning standardized JSON error structure:
    {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Human readable error summary",
            "details": { ... field specific errors ... }
        }
    }
    """
    if isinstance(exc, DjangoValidationError):
        # Domain/service-layer validation errors -> structured 400 instead of a 500.
        detail = exc.message_dict if hasattr(exc, "error_dict") else exc.messages
        exc = DRFValidationError(detail=detail)

    response = exception_handler(exc, context)

    if response is not None:
        status_code = response.status_code
        error_code = getattr(exc, "default_code", "API_ERROR")
        if isinstance(error_code, str):
            error_code = error_code.upper()

        message = str(exc)
        if hasattr(exc, "detail") and isinstance(exc.detail, dict):
            details = exc.detail
            message = "Validation failed for one or more fields."
        elif hasattr(exc, "detail") and isinstance(exc.detail, list):
            details = exc.detail
        else:
            details = response.data if isinstance(response.data, (dict, list)) else {}

        custom_response_data = {
            "error": {
                "code": error_code,
                "message": message,
                "details": details,
            }
        }
        return Response(custom_response_data, status=status_code)

    return response
