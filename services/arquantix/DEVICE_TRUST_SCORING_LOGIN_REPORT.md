# Device trust & scoring login — rapport d’implémentation

## Executive Summary

Mise en place d’un **profil device par utilisateur** (`auth_user_device_profiles`) et d’une **chaîne de décision login** réutilisant le **hash device** existant, la **réputation globale**, le **score global** (`auth_global_risk_score`), les **passkeys** et les **sessions** — **sans** nouveau moteur de risque parallèle au SIEM / `security_response_engine`.

Les décisions sont **explicables** (signaux nommés, codes `reason_codes`) et journalisées dans **`auth_security_decisions`** + événement **`auth.login.strategy_evaluated`** lorsque les événements sécurité sont activés.

## Data Model

| Table | Rôle |
|--------|------|
| `auth_user_device_profiles` | Une ligne par `(user_id, device_hash)` : compteurs login, dernière IP/pays, empreinte, `trust_score` / `trust_level` (LOW/MEDIUM/HIGH), derniers champs attestation / `auth_strength`. |

Migration : `api/alembic/versions/118_auth_user_device_profiles.py`  
ORM : `AuthUserDeviceProfile` dans `api/database.py`.

## Trust Scoring Logic

Fichier : `api/services/security/login_device_trust_service.py`

- **`compute_device_trust_score`** : agrégation déterministe 0–100 (ancienneté, succès/échecs, stabilité empreinte/pays, bonus attestation, pénalités `auth_device_reputation`).
- **`compute_device_trust_level`** : seuils 44 / 72 → LOW / MEDIUM / HIGH.
- **`resolve_user_device_profile`** / **`update_user_device_profile_on_login`** : lecture / upsert après tentative (succès ou échec).
- **`session_device_trust_from_profile_level`** : mapping vers les valeurs déjà utilisées dans `auth_sessions.device_trust_level` (TRUSTED / UNKNOWN / SUSPICIOUS).

## Login Risk Evaluation

Fichier : `api/services/security/login_context_risk.py`

- **`evaluate_login_context_risk(user, device_hash, …)`** retourne :
  - `device_trust_score`, `device_trust_level`
  - `login_risk_score` (0–100, **plus haut = plus risqué**) combinant inverse du trust device et le **score global stocké** (pas de recalcul moteur complet ici)
  - `signals` (liste de chaînes : nouveau device, empreinte changée, blacklist, risque global élevé, etc.)
  - `decision_hint` : `otp_only` | `otp_step_up` | `passkey_preferred` | `blocked`

Seuil de blocage contextuel : variable d’environnement **`LOGIN_CONTEXT_BLOCK_MIN_SCORE`** (défaut **96**).

## Login Decision Strategy

Fichier : `api/services/security/login_auth_strategy_service.py`

- **`decide_login_auth_strategy`** → `LoginAuthStrategyResult` :
  - `primary_method` : `otp` ou `passkey` (recommandation UX si passkeys enregistrées + device peu fiable)
  - `step_up_required`, `blocked`, `reason_codes`
  - `session_trust_flag` : aligné sur le mapping session
- **`enforce_login_strategy_or_raise`** : utilisé dans **`issue_fresh_auth_session`** (403 si bloqué).
- **`persist_login_strategy_decision`** : `auth_security_decisions` avec `policy_id = login.auth_strategy.v1`.
- **`merge_device_trust_for_session`** : conserve le niveau **le plus strict** entre l’appelant (ex. OTP « TRUSTED ») et la stratégie.

### Variables d’environnement

| Variable | Défaut | Effet |
|----------|--------|--------|
| `LOGIN_DEVICE_TRUST_ENABLED` | `true` | Profils + mise à jour post-login |
| `LOGIN_AUTH_STRATEGY_ENABLED` | `true` | Décision + enforcement + champs réponse start |
| `LOGIN_STRATEGY_PERSIST_DECISIONS` | `true` | Écriture `auth_security_decisions` |
| `LOGIN_CONTEXT_BLOCK_MIN_SCORE` | `96` | Blocage contexte (`decision_hint = blocked`) |

## Backend Integration

1. **`issue_fresh_auth_session`** (`refresh_session.py`)  
   - Résout `device_hash` si réputation **ou** trust **ou** stratégie active.  
   - Enchaîne réputation existante → **stratégie** → fusion `step_up` / `device_trust_level`.  
   - **`update_user_device_profile_on_login`** (succès) avant `commit`.

2. **OTP mobile** `POST /auth/login/sms/start`  
   - `decide_login_auth_strategy` + persistance décision ; **403** si `blocked`.  
   - Réponse enrichie : `auth_strategy_hint`, `primary_auth_method`, `step_up_recommended`.

3. **OTP mobile verify** (code incorrect)  
   - Incrément **`failed_login_count`** sur le profil si trust activé.

4. **Admin e-mail OTP start**  
   - Même garde-fou stratégie + persistance avant envoi mail.

5. **Passkeys / mot de passe**  
   - Passent par **`issue_fresh_auth_session`** → stratégie + profil sans dupliquer la logique dans `passkeys_service` / `perform_login`.

## Tests

Fichier : `api/tests/test_login_device_trust.py`

- Device connu → trust élevé  
- Nouveau device → trust faible / signaux  
- Changement d’empreinte → signal explicite  
- Blacklist → `blocked`  
- Compte suspect (score global HIGH) → step-up ou passkey  
- Passkey enregistrée → `primary_method == passkey` sur device neuf  
- Composantes score monotones (attestation / empreinte)  
- Compteurs profil succès/échec  

Les tests **`test_mobile_sms_login_otp`** restent verts.

## Remaining Gaps

- **Géolocalisation IP** : `last_country` repose sur en-têtes type `CF-IPCountry` / `X-Geo-Country` si présents ; pas de GeoIP serveur intégré ici.
- **Cache décision start → verify** : la stratégie est réévaluée à l’ouverture de session (cohérent mais double évaluation par flux).
- **Step-up produit** : les drapeaux `step_up_recommended` / `step_up_otp_required` côté session existaient déjà ; l’app mobile peut consommer les nouveaux champs start pour UX (ex. pousser passkey).
- **`is_primary`** : colonne préparée, pas encore alimentée par un flux métier dédié.
- **Seuils** : calibrage fin (OTP vs passkey vs blocage) devrait suivre données réelles et A/B conformité.
