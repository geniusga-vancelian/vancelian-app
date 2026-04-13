"""
Custom exceptions for Bundles service
"""
from fastapi import HTTPException, status


class BundleValidationError(HTTPException):
    """Raised when bundle validation fails"""
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class BundleCycleError(HTTPException):
    """Raised when a cycle is detected in bundle composition"""
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cycle detected in bundle composition: {detail}")


class DynamicRuleInvalid(HTTPException):
    """Raised when dynamic rule JSON is invalid"""
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid dynamic rule: {detail}")


class InsufficientMarketData(HTTPException):
    """Raised when insufficient market data is available for preview/calculation"""
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Insufficient market data: {detail}")

