"""Fichiers publics .well-known (AASA, Digital Asset Links) pour passkeys mobiles."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.auth.webauthn_config import (
    android_assetlinks_targets_from_env,
    build_apple_app_site_association,
)

router = APIRouter(tags=["well-known"])

# Apple recommande application/json ; pas de charset problématique pour certains validateurs.
_AASA_CT = "application/json"
_ASSETLINKS_CT = "application/json"


def _no_store() -> dict:
    return {"Cache-Control": "public, max-age=300"}


@router.get("/.well-known/apple-app-site-association")
def apple_app_site_association_well_known():
    body = build_apple_app_site_association()
    return JSONResponse(
        content=body,
        media_type=_AASA_CT,
        headers=_no_store(),
    )


@router.get("/apple-app-site-association")
def apple_app_site_association_root():
    """Compatibilité : certains reverse proxies / CDN cherchent ce chemin."""
    return apple_app_site_association_well_known()


@router.get("/.well-known/assetlinks.json")
def assetlinks_well_known():
    targets = android_assetlinks_targets_from_env()
    return JSONResponse(
        content=targets,
        media_type=_ASSETLINKS_CT,
        headers=_no_store(),
    )
