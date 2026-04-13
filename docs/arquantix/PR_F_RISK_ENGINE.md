# PR F — Risk Engine antifraude (niveau banque)

## Objectif

Couche **déterministe** (sans ML) qui agrège des signaux device, réseau, comportement et session pour produire :

- un **`risk_score`** entier **0–100** ;
- une décision **`allow` | `step_up` | `block`** ;
- une journalisation structurée **`device_risk_evaluated`** ;
- une mise à jour de **`auth_user_device_profiles`** (`last_ip`, `last_country`, `last_seen_at`, `device_id`).

## Activation

| Variable | Défaut | Rôle |
|----------|--------|------|
| `DEVICE_RISK_ENGINE_PR_F_ENABLED` | `false` | Maître : désactivé → aucun changement de comportement (hors imports). |
| `DEVICE_RISK_ALLOW_THRESHOLD` | `40` | Scores **&lt;** cette valeur → `allow`. |
| `DEVICE_RISK_BLOCK_THRESHOLD` | `70` | Scores **≥** cette valeur → `block`. |
| `DEVICE_RISK_STEP_UP_THRESHOLD` | *(informatif)* | Zone **step_up** = \[`ALLOW_THRESHOLD`, `BLOCK_THRESHOLD`). Même borne basse que `ALLOW` si non utilisée ailleurs. |
| `DEVICE_RISK_ATTESTATION_STALE_DAYS` | `30` | Au-delà, attestation considérée « stale » (+20). |
| `DEVICE_RISK_ENGINE_PR_F_CACHE_TTL_SEC` | `0` | Réservé (cache futur / Redis) ; **0** = pas de cache processus. |

## Audit des signaux (référentiel)

| Catégorie | Signal | Stockage / source | Fréquence |
|-----------|--------|-------------------|-----------|
| Device | `device_id`, empreinte | En-têtes, `auth_device_credentials`, `auth_user_device_profiles.device_hash` | À la requête / login |
| Device | `device_trust_level` | `auth_sessions.device_trust_level`, profil `trust_level` | Session + profil |
| Device | Attestation | `auth_sessions.attestation_*`, PR E | Refresh / route |
| Session | `auth_sessions`, `last_used_at`, `revoked_at` | PostgreSQL | Continu |
| Réseau | IP | `X-Forwarded-For`, `request.client` | Par requête |
| Réseau | Pays | `CF-IPCountry`, `X-Country-Code` | Par requête |
| Comportement | Échecs signature | `device_signature_failure_rl` (mémoire PR D3) | Fenêtre 60 s |
| Comportement | Vélocité actions sensibles | `device_sensitive_action_velocity` (PR D4) | Fenêtre 300 s |
| Comportement | Login / refresh refusés | `auth_security_events` (`auth.login.failed`, `auth.refresh.rejected`) | 1 h glissante |
| Comportement | Churn devices | `COUNT(DISTINCT device_id)` sur `auth_sessions` 24 h | Par évaluation |
| Historique | Dernière IP / pays | `auth_user_device_profiles` | Mis à jour après chaque évaluation PR F |

## Modèle de score (implémenté)

Les pondérations sont cumulées puis plafonnées à **100** (voir `compute_risk_score` dans `services/auth/device_risk_engine_pr_f.py`) :

- **Trust** : LOW +40, MEDIUM +15, HIGH +0, inconnu +25.
- **Attestation** : absente +40 ; périmée +20 (si une date existe).
- **Réseau** : changement IP +15 ; changement pays +25 (si les deux côtés connus).
- **Comportement** : vélocité élevée (&gt; 3) +20 ; échecs signature récents +min(30, n×15) ; churn (2 devices / 3+ devices) +12 / +25.
- **Session** : session « récente » (&lt; 10 min) +10.
- **Auth** : échecs login/refresh récents +min(20, 5×(login+refresh)).

## Décision

- `score < DEVICE_RISK_ALLOW_THRESHOLD` → **allow**
- `DEVICE_RISK_BLOCK_THRESHOLD ≤ score` → **block**
- sinon → **step_up**

## Réponses HTTP

- **step_up** : `403` avec `error: device_risk_step_up`, `step_up: true`, `risk_score`.
- **block** : `403` avec `error: device_risk_blocked`, `step_up: false`, `risk_score`.
- **Device ID manquant** (évaluation activée) : `403` avec message explicite (aligné routes sensibles PR E).

## Intégration FastAPI

Dépendance : `require_low_risk_action()` dans `services/auth/device_risk_pr_f_dependencies.py`.

Routes custody concernées (après `require_continuous_auth_for_action` et `require_device_attestation`) :

- création comptes client / bénéficiaires (`beneficiary_add`) ;
- retrait simulé / replay webhook (`withdrawal`) ;
- `POST /api/internal-transfer` (`wallet_transfer`).

## Journalisation

Événement logger : **`device_risk_evaluated`** avec champs `user_id`, `device_id` (préfixe), `risk_score`, `decision`, `ip`, `country`, `route`.

## Tests

`services/arquantix/api/tests/test_device_risk_engine_pr_f.py`

## Cohabitation PR D / PR E

- **PR D4** : score et politique **spécifiques** aux routes avec signature device (`device_risk_pr_d4.py`) — inchangé.
- **PR E** : attestation matérielle — inchangé ; PR F s’exécute **après** les mêmes `Depends` sur les routes custody listées.

Aucun chemin n’est modifié si `DEVICE_RISK_ENGINE_PR_F_ENABLED=false`.
