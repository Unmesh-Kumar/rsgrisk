class ESGServiceError(Exception):
    """Base exception for ESG service issues."""


class ExternalAPIError(ESGServiceError):
    """Raised when an upstream API fails."""

