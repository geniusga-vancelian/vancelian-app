"""Bundle on-chain execution abstraction (Phase 1).

Orchestrators delegate to ``BundleExecutionAdapter``; providers encapsulate
Exchange (active) and LI.FI (skeleton, feature-flagged off).
"""
from .bundle_execution_adapter import BundleExecutionAdapter
from .config import get_bundle_execution_provider_name
from .providers import get_execution_provider
from .types import ExecutionLeg, ExecutionQuote, ExecutionResult

__all__ = [
    "BundleExecutionAdapter",
    "ExecutionLeg",
    "ExecutionQuote",
    "ExecutionResult",
    "get_bundle_execution_provider_name",
    "get_execution_provider",
]
