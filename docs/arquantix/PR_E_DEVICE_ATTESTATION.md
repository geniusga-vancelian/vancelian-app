# PR E — Attestation matérielle obligatoire (policy)

## Phase 1 — Audit (état du code)

### Où l’attestation est vérifiée aujourd’hui

| Fichier / symbole | Rôle |
|-------------------|------|
| `services/auth/device_attestation_service.py` | `verify_device_attestation`, `_verify_apple_app_attest`, `_verify_play_integrity`, `evaluate_header_for_auth`, `parse_x_device_attestation_header` |
| `services/auth/device_credentials_routes.py` | Liaison PR D3 `pk_sha256` si `REGISTER_KEY_PK_ATTESTATION_BINDING` |
| `services/auth/refresh_session.py` | Login + refresh : `evaluate_header_for_auth`, mise à jour `auth_sessions.attestation_*` |

### Où elle était optionnelle (avant PR E)

| Flux | Comportement |
|------|----------------|
| `POST /auth/login` | Attestation seulement si `DEVICE_ATTESTATION_ENABLED` ; sinon ignorée |
| `POST /auth/refresh` | Idem + bloc optionnel si en-tête présent |
| `POST /auth/device/register-key` | Attestation obligatoire seulement si `REGISTER_KEY_PK_ATTESTATION_BINDING` |

### Où `device_trust_level` / attestation est écrit

| Emplacement | Champ |
|-------------|--------|
| `auth_sessions` | `device_trust_level`, `attestation_type`, `attestation_verified_at`, `attestation_metadata`, **PR E : `device_attestation_tier`** |
| `auth_device_credentials` | `attestation_level`, `attestation_bound_at` |
| JWT access | `dtrust` (via `device_trust` à l’émission) |
| `auth_user_device_profiles` | `last_attestation_level` (login trust service) |

### Routes sans contrôle attestation dédié (avant PR E)

- La plupart des routes métier (custody, transferts, etc.) : uniquement **continuous auth** / Zero Trust si activés, pas de preuve App Attest/Play Integrity dédiée.

---

## Tableau PR E — `attestation_required` (policy `DEVICE_ATTESTATION_REQUIRED_SENSITIVE`)

Ces routes incluent `Depends(require_device_attestation())` : **effet seulement si** `DEVICE_ATTESTATION_REQUIRED_SENSITIVE=true`.

| Route | `attestation_required` (si flag ON) |
|-------|-------------------------------------|
| `POST /api/admin/custody/accounts/client` | **true** |
| `POST /api/admin/custody/accounts/client/canonical` | **true** |
| `POST /api/admin/custody/accounts/client/simple-create` | **true** |
| `POST /api/admin/custody/webhook-events/{id}/replay` | **true** |
| `POST /api/admin/custody/simulate-withdrawal` | **true** |
| `POST /api/internal-transfer` | **true** |
| `PATCH /api/app/flutter/profile/security-preferences` | **true** (dépendance mobile `require_device_attestation_mobile`) |

Routes **publiques** ou non listées : inchangées.

---

## Trust model (LOW / MEDIUM / HIGH)

Implémentation : `compute_attestation_trust_level` dans `device_attestation_trust.py`.

- **HIGH** : assertion cryptographique forte récente + liaison clé (`attestation_bound_at`) lorsque requis par la politique.
- **MEDIUM** : attestation valide mais plus ancienne, ou type intermédiaire.
- **LOW** : absence de signal fiable.

---

## Variables d’environnement

| Variable | Défaut | Effet |
|----------|--------|--------|
| `DEVICE_ATTESTATION_REQUIRED_LOGIN` | `false` | Login (device réel) exige en-tête valide |
| `DEVICE_ATTESTATION_REQUIRED_REFRESH` | `false` | Refresh exige en-tête valide |
| `DEVICE_ATTESTATION_REQUIRED_SENSITIVE` | `false` | Routes listées : `require_device_attestation` |
| `DEVICE_TRUST_REQUIRED_LEVEL` | `HIGH` | Seuil minimal (`HIGH` / `MEDIUM` / `LOW`) |
| `DEVICE_ATTESTATION_REFRESH_MAX_AGE_SEC` | `86400` | Après ce délai, refresh exige nouvelle attestation si `DEVICE_ATTESTATION_REFRESH_STRICT_ON_D3` + `DEVICE_SECURITY_LEVEL>=3` |
| `DEVICE_ATTESTATION_REFRESH_STRICT_ON_D3` | `true` | Active la contrainte de fraîcheur au refresh en niveau 3 |
| `DEVICE_ATTESTATION_TIER_HIGH_MAX_AGE_SEC` | `86400` | Âge max pour conserver un **HIGH** à partir de la session seule |

---

## Logs structurés

- `device_attestation_required` — attestation absente ou tier LOW sur route protégée.
- `device_trust_level_insufficient` — tier présent mais inférieur au seuil requis.

---

## Migrations

- **135** : colonne `auth_sessions.device_attestation_tier` (`VARCHAR(16)`, nullable).

---

## Compatibilité

- Tous les flags **désactivés par défaut** : aucun changement de comportement sans configuration explicite.
- PR B / C / D (dont PR D4) non modifiés dans leur logique ; PR E s’ajoute par couches.
