"""Custom application exceptions"""

from fastapi import HTTPException, status


class PerfumeChemException(Exception):
    """Base exception for the application"""
    pass


class EntityNotFoundError(PerfumeChemException):
    """Raised when a requested entity is not found"""
    
    def __init__(self, entity: str, entity_id: int | str):
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} with id {entity_id} not found")


class AIServiceError(PerfumeChemException):
    """Raised when AI service encounters an error"""
    
    def __init__(self, message: str, original_error: Exception | None = None):
        self.original_error = original_error
        super().__init__(message)


class ValidationError(PerfumeChemException):
    """Raised when validation fails"""
    
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Validation error on {field}: {message}")


class IFRAComplianceError(PerfumeChemException):
    """Raised when a formula violates IFRA guidelines"""
    
    def __init__(self, ingredient: str, limit: float, actual: float):
        self.ingredient = ingredient
        self.limit = limit
        self.actual = actual
        super().__init__(
            f"IFRA violation: {ingredient} at {actual}% exceeds limit of {limit}%"
        )


class ChemicalIncompatibilityError(PerfumeChemException):
    """Raised when incompatible chemicals are combined"""
    
    def __init__(self, chemical1: str, chemical2: str, reason: str):
        self.chemical1 = chemical1
        self.chemical2 = chemical2
        self.reason = reason
        super().__init__(
            f"Incompatible combination: {chemical1} + {chemical2}. Reason: {reason}"
        )


class DilutionCalculationError(PerfumeChemException):
    """Raised when dilution calculation fails"""
    pass


class FormulaBalanceError(PerfumeChemException):
    """Raised when formula percentages don't sum to 100%"""
    
    def __init__(self, total: float):
        self.total = total
        super().__init__(f"Formula ingredients sum to {total}%, must be 100%")


# HTTP Exception helpers
def not_found(entity: str, entity_id: int | str) -> HTTPException:
    """Create 404 Not Found exception"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity} with id {entity_id} not found"
    )


def bad_request(message: str) -> HTTPException:
    """Create 400 Bad Request exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message
    )


def internal_error(message: str = "Internal server error") -> HTTPException:
    """Create 500 Internal Server Error exception"""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=message
    )


def unauthorized(message: str = "Not authenticated") -> HTTPException:
    """Create 401 Unauthorized exception"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden(message: str = "Not enough permissions") -> HTTPException:
    """Create 403 Forbidden exception"""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=message
    )
