"""
Bundle validation errors
"""
from typing import Optional


class BundleValidationError(Exception):
    """Raised when bundle weights are invalid"""
    def __init__(self, message: str, bundle_id: Optional[int] = None):
        self.message = message
        self.bundle_id = bundle_id
        super().__init__(self.message)

