# FAKE_SMS_PROVIDER — Rapport

## Executive Summary

Un **faux fournisseur SMS** (`FakeSmsProvider`) simule un envoi OTP réussi **sans appel réseau**, sélectionné par `get_sms_provider()` lorsque l’environnement **n’est pas** production-like et que **`FAKE_SMS_PROVIDER`** est truthy. En **production / prod / staging**, le fake est **interdit** : `get_sms_provider()` lève une erreur et le **config guard** au boot refuse la configuration. Le flux métier (`create_challenge`, `send_code`, audit `two_factor.challenge.sent`, `verify`) reste **identique** à Twilio ; seul le transport est simulé.

## Provider Design

- Fichier : `api/services/security/providers/fake_sms_provider.py`
- Sous-classe de `SmsProvider` : `is_noop == False` (canal SMS utilisable même en mode strict, comme Twilio).
- `send_otp(to_e164, code, *, challenge_id=None)` : aucun HTTP ; log structuré JSON (`event`, `target_masked`, `challenge_id`, `code`) après garde **RuntimeError** si jamais appelé en env production-like.
- `audit_provider_key = "fake_sms"` pour les payloads d’audit côté `TwoFactorService.send_code`.

L’interface `SmsProvider.send_otp` accepte désormais un **`challenge_id` optionnel** (keyword-only) ; `TwilioSmsProvider` et `NoopSmsProvider` sont alignés ; `two_factor_service` passe `challenge_id=str(challenge.id)`.

## Environment Guards

1. **`get_sms_provider()`** (`sms_provider.py`)  
   - Si `is_production_like_env()` et `FAKE_SMS_PROVIDER` truthy → **`RuntimeError`** (fail-fast à chaque résolution).  
   - Si non prod-like et flag truthy → **`FakeSmsProvider`**.  
   - Sinon Twilio si creds, sinon `NoopSmsProvider`.

2. **`run_two_factor_config_guard()`** (`two_factor_config_guard.py`)  
   - En env production-like : si `FAKE_SMS_PROVIDER` truthy → erreur agrégée **`TwoFactorConfigGuardError`** au boot (même logique que les autres contraintes prod).

## Logging Behavior

- Logs **uniquement** depuis `FakeSmsProvider` (jamais instancié en prod-like).  
- Ligne unique `INFO` avec JSON : cible masquée, `challenge_id`, **code en clair** (acceptable **uniquement** en dev/test car le provider n’existe pas en prod).  
- Twilio / prod : comportement inchangé (pas de log du code OTP côté noop existant).

## Tests Added

Fichier : `api/tests/test_fake_sms_provider.py`

- Résolution `FakeSmsProvider` en dev + flag.  
- Interdiction en `APP_ENV=production`.  
- Config guard rejette `FAKE_SMS_PROVIDER` en prod.  
- `/api/2fa/start` SMS + audit `provider=fake_sms` + `verify` OK (OTP contrôlé par patch de `_generate_numeric_code`, `TWO_FACTOR_DEV_FIXED_CODE` désactivé dans le test pour éviter les collisions avec un `.env` local).  
- `httpx.Client` du module Twilio **non appelé** quand le fake est actif.

Ajustement : `test_sms_provider_failure_returns_503` compte les challenges **par `person_id`** pour éviter les faux positifs si d’autres lignes existent dans la table.

## Remaining Gaps

- **Email** : pas d’équivalent `FAKE_EMAIL_PROVIDER` (hors périmètre demandé).  
- Les audits **`standalone`** sur échec d’envoi utilisent `SessionLocal()` ; si la `Person` n’existe que dans la transaction de test, l’insert audit peut échouer (FK) — déjà géré en best-effort ; pas modifié ici.
