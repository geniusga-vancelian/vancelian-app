"""P2P Internal Lending Engine — Phase 2A → 2A.10."""
from .router import router as lending_router
from .wealth_router import router as wealth_router
from .pool_router import router as pool_router
from .interest_router import router as interest_router
from .product_router import router as product_router
from .offer_router import router as offer_router

__all__ = [
    "lending_router", "wealth_router", "pool_router",
    "interest_router", "product_router", "offer_router",
]
