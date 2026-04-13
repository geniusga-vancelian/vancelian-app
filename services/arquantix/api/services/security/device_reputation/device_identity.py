"""
Stratégie d’identité device : ne pas s’appuyer sur un seul identifiant spoofable.

Principes
---------

1. **Empreinte matérielle** (`fingerprint_hash`, ex. en-tête ``X-Device-Fingerprint``) est
   l’ancre préférée lorsqu’elle est présente : elle est concaténée en premier dans le matériau
   de hachage pour maximiser la stabilité entre sessions du même appareil.

2. **`device_id` client** (souvent UUID install) est ajouté en complément quand il n’est pas
   la valeur legacy ; il renforce la corrélation quand la fingerprint manque.

3. **`install_id`** (ex. ``X-Install-ID``) permet de distinguer des réinstallations / clones si
   le client le fournit ; optionnel.

4. **Forme canonique** : segments triés ``fp:`` / ``did:`` / ``inst:`` en minuscules,
   puis **SHA-256 hex** (64 caractères). Aucun secret : uniquement corrélation interne.

5. **Legacy** : sans fingerprint ni device_id exploitable, on retombe sur ``did:legacy-unknown``
   (réputation peu discriminante — à interpréter avec prudence).

Toute décision de blocage repose sur des règles explicites (seuils, blacklist admin), pas sur
le seul hash.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

_LEGACY = "legacy-unknown"
_MAX_SEGMENT = 256


def _seg(s: Optional[str]) -> str:
    if s is None:
        return ""
    t = str(s).strip().lower()
    if len(t) > _MAX_SEGMENT:
        t = t[:_MAX_SEGMENT]
    return t


def normalize_device_identity(
    device_id: Optional[str],
    fingerprint_hash: Optional[str] = None,
    install_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Représentation normalisée des composants (audit / logs structurés)."""
    did = _seg(device_id) or _LEGACY
    if did == _LEGACY and not _seg(fingerprint_hash) and not _seg(install_id):
        did_norm = _LEGACY
    else:
        did_norm = did
    return {
        "device_id_normalized": did_norm,
        "fingerprint_present": bool(_seg(fingerprint_hash)),
        "install_id_present": bool(_seg(install_id)),
    }


def build_device_hash(
    device_id: Optional[str],
    fingerprint_hash: Optional[str] = None,
    install_id: Optional[str] = None,
) -> str:
    """
    Construit un hash stable 64 hex à partir des identifiants disponibles.

    L’ordre des segments dans le matériau canonique est fixe : fp → did → inst
    (pas de tri alphabétique) pour la reproductibilité inter-services.
    """
    fp = _seg(fingerprint_hash)
    did = _seg(device_id)
    inst = _seg(install_id)

    parts: list[str] = []
    if fp:
        parts.append(f"fp:{fp}")

    if did and did != _LEGACY:
        parts.append(f"did:{did}")
    elif not parts:
        parts.append(f"did:{_LEGACY}")

    if inst:
        parts.append(f"inst:{inst}")

    canonical = "|".join(parts)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
