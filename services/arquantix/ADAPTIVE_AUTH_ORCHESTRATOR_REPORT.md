# Executive Summary

Un **orchestrateur unique** (`adaptive_auth_orchestrator.py`) centralise la décision de parcours de connexion (passkey, OTP SMS/e-mail, blocage) à partir des signaux existants : confiance appareil, risque global, fraude/ML, passkeys, attestation. Les routes et écrans actuels **exécutent** les flux ; l’orchestrateur ne remplace pas une deuxième stack. Les décisions sont **explicables** (`reason_codes`, `ui_variant`) et **journalisées** (événement `auth.login.orchestrated` + persistance `auth_security_decisions`). Le mobile consomme le champ optionnel `orchestrator` dans `sms/start` et route vers passkey auto, OTP (standard / prudent) ou écran bloqué.

# Existing Building Blocks Reused

- **Contexte d’évaluation login** : `build_login_evaluation_context` / `login_auth_strategy_service` (device, risque, stratégie historique).
- **Device trust** : profils appareil et niveaux (`login_device_trust_service`, `session_device_trust_from_profile_level`).
- **Fraude** : `login_fraud_evaluator` (score hybride / ML lorsque activé).
- **Passkeys** : éligibilité et credentials via le même pipeline que les starts existants.
- **Événements sécurité** : `persist_auth_security_event` + modèle `AuthSecurityDecision`.

# Orchestrator Architecture

- **Fichier principal** : `api/services/auth/adaptive_auth_orchestrator.py`.
- **Modèle** : `AdaptiveAuthDecision` (méthode primaire, replis, flags step-up / biométrie locale, scores, cibles session, `ui_variant`).
- **Entrée** : `orchestrate_login_strategy` / `orchestrate_login_strategy_from_request` avec builders (`build_device_context_*`, `build_risk_context_*`, `build_fraud_context`, `build_passkey_context`, `build_attestation_context`, `build_user_login_context`).
- **Persistance** : `persist_adaptive_auth_decision` (SIEM + ligne décision avec `policy_id` adaptatif).

# Decision Model

Règles prioritaires (ordre stable) : compte / appareil bloqués ou risque critique → `blocked` ; device **HIGH** + passkey + risque faible → passkey avec `auto_trigger_passkey` (si flag) et repli OTP ; confiance moyenne / modérée → OTP SMS ; device faible ou fraude élevée → OTP + `step_up_required` ; sans mobile mais e-mail → `otp_email` (si fallback e-mail activé) ; aucun moyen sûr → `blocked` avec codes explicites.

# Backend Integration

- **Stratégie login** : `decide_login_auth_strategy` délègue à l’orchestrateur lorsque `ADAPTIVE_AUTH_ENABLED=true`.
- **Points branchés** (non exhaustif) : `mobile_otp_login_routes` (SMS start), admin e-mail OTP start, passkey login start (blocage si décision `blocked`), refresh session enrichi, `POST /auth/login/orchestrate` (`adaptive_auth_routes.py`).
- **Schémas** : `AdaptiveAuthOrchestrateRequest`, `AdaptiveAuthDecisionPayload` dans `schemas.py`.

# Flutter Integration

- **Couche** : `mobile/lib/features/auth/orchestrator/login_orchestrator.dart` — `LoginOrchestratorResult.fromSmsStartResponse` + `pushFlow`.
- **Écran téléphone** : `login_phone_screen.dart` utilise l’orchestrateur au lieu de dupliquer la logique `recommended_auth_method`.
- **API optionnelle** : `PasskeyApi.adaptiveLoginOrchestrate` → `POST /auth/login/orchestrate` (pré-décision avec en-têtes device).
- **Bloqué** : `login_blocked_screen.dart`.

# UX Variants

- **fast_lane** : titres optionnels sur `LoginAutoAuthScreen` (« Connexion sécurisée en cours… »).
- **standard** : `LoginOtpScreen` sans message additionnel.
- **cautious** : `LoginOtpScreen` avec `extraSecurityMessage` (step-up visible, texte rassurant).
- **blocked** : écran dédié avec codes affichables pour support.

# Session Trust Targeting

Champs portés par la décision : `auth_strength_target`, `session_trust_target`, `local_biometric_recommended`. Consommation côté émission de session / politique de relock : à aligner progressivement avec `issue_fresh_auth_session` et la politique biométrique locale (les hooks métadonnées refresh enrichissent déjà le fil).

# Events / SIEM

- **Type** : `auth.login.orchestrated`.
- **Payload** (extrait) : `primary_method`, `fallback_methods`, `blocked`, `reason_codes`, `device_trust_level`, `login_risk_score`, `fraud_score`, `ui_variant`.
- **Table** : réutilisation / enregistrement via `auth_security_decisions` (policy adaptive).

# Tests

- **Python** : `api/tests/test_adaptive_auth_orchestrator.py` (scénarios décisionnels).
- **Flutter** : `mobile/test/features/auth/login_orchestrator_test.dart` (mapping JSON → route).

# Rollout Strategy

Variables d’environnement :

- `ADAPTIVE_AUTH_ENABLED` (défaut **false** — activation maîtrisée).
- `ADAPTIVE_AUTH_PASSKEY_AUTO`
- `ADAPTIVE_AUTH_BLOCK_HIGH_RISK`
- `ADAPTIVE_AUTH_EMAIL_FALLBACK`

Recommandation : activer d’abord en staging, surveiller `auth.login.orchestrated` et le log admin preview, puis production par paliers.

# Remaining Gaps

- Login **mot de passe** : branchement explicite sur l’orchestrateur si le flux reste exposé (optionnel selon produit).
- **Cibles session** : propagation systématique vers relock / grace period selon `session_trust_target` (à finaliser si pas déjà uniforme).
- **OTP e-mail côté mobile** : routage dédié si `primary_method == otp_email` hors admin (selon parcours grand public).
- **Double journalisation** : cohabitation possible avec d’anciens événements « strategy » — documenter la source de vérité opérationnelle pendant la migration.

# Admin / Debug

- `GET /admin/security/auth-orchestrator/preview?user_id=...`
- `GET /admin/security/auth-orchestrator/decision-log`

(Accès conforme aux garde-fous admin existants.)
