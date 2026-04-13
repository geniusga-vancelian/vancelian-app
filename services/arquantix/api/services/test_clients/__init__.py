"""Routes app mobile (/api/app/*) — données portfolio liées au JWT.

Ne pas importer ``router`` au chargement du package : évite un cycle
``database → test_clients (snapshot model) → router → database``.
"""


def __getattr__(name: str):
    if name == "bootstrap_router":
        from .router import bootstrap_router

        return bootstrap_router
    if name == "mobile_flutter_router":
        from .router import mobile_flutter_router

        return mobile_flutter_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["bootstrap_router", "mobile_flutter_router"]
