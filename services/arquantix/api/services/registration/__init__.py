from .runtime_router import router as registration_runtime_router
from .admin_router import router as registration_admin_router
from .jurisdiction_policy_admin_router import (
    router as jurisdiction_policy_admin_router,
    legacy_router as jurisdiction_policy_legacy_router,
    country_directory_admin_router,
)
