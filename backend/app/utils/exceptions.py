"""
Custom HTTP exceptions for consistent error responses.
"""
from fastapi import HTTPException, status


class NotFoundException(HTTPException):
    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found.",
        )


class UnauthorizedException(HTTPException):
    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(HTTPException):
    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message,
        )


class ConflictException(HTTPException):
    def __init__(self, message: str = "Resource already exists.") -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )


class BadRequestException(HTTPException):
    def __init__(self, message: str = "Bad request.") -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )


class ServiceUnavailableException(HTTPException):
    def __init__(self, message: str = "AI service is temporarily unavailable.") -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=message,
        )
