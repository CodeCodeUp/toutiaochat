from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundException(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            detail=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN
        )


class AIServiceException(AppException):
    def __init__(self, detail: str = "AI service error"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class PublishException(AppException):
    def __init__(self, detail: str = "Publish failed"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
