# Runbook — E2E vérification téléphone (SMS) sans SMS réel

## Variables d’environnement (API)

À définir **avant** de lancer l’API (fichier `api/.env` ou export shell) :

| Variable | Valeur | Rôle |
|----------|--------|------|
| `APP_ENV` | `development` (ou autre **non** production/prod/staging) | Active le code OTP fixe et le fake SMS |
| `TWO_FACTOR_RELAXED` | `true` | Mode dev/tests (noop email possible, purposes assouplis) |
| `TWO_FACTOR_DEV_FIXED_CODE` | `111111` | OTP SMS/email déterministe (hashé en base comme en prod) |
| `TWO_FACTOR_DEV_EXPOSE_CODE` | `true` | (Optionnel) expose `dev_code` dans prepare/resend / 2FA start |
| `FAKE_SMS_PROVIDER` | `true` | Simule l’envoi SMS sans Twilio |
| `TWO_FACTOR_REQUIRE_AUTH` | `false` | (Optionnel dev) pour tests directs sur `/api/2fa/*` avec `person_id` body |

Ne **pas** utiliser ces valeurs sur **production** ou **staging** : le garde-fou `is_production_like_env()` et `run_two_factor_config_guard` bloquent le fake SMS et invalident le code fixe en prod-like.

## Lancer l’API

```bash
cd services/arquantix/api
# Dépendances + DB migrée (incl. registration + 2FA)
alembic upgrade head
uvicorn main:app --reload --port 8000
```

Adapter le port selon votre `START_SERVERS.md` / reverse proxy.

## Lancer Flutter

```bash
cd services/arquantix/mobile
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

Sur émulateur Android, remplacer par `http://10.0.2.2:8000` si besoin.

## Numéro et OTP de test

- **Numéro** : tout E.164 valide accepté par le moteur (ex. `+33612345678` ou `+33701999888`). Avec `FAKE_SMS_PROVIDER=true`, aucun SMS réel n’est envoyé.
- **Code OTP attendu** : **`111111`** (tant que `TWO_FACTOR_DEV_FIXED_CODE=111111`).

En build **debug**, l’écran OTP inline affiche un rappel : *Dev — test OTP 111111…* (`RegistrationPhoneSmsOtpPanel`). Absent en **release** (`kDebugMode`).

## Scénario manuel (smoke QA)

1. Ouvrir le flux d’inscription sur une juridiction dont le flow actif contient :
   - un écran **formulaire** avec `phone_input` lié à `phone_number` ;
   - puis un écran **interaction** `phone_verification_sms` (`source_field_slug` / `verified_flag_slug` / `purpose` configurés).
2. Saisir le numéro sur l’écran téléphone et valider (**submit**).
3. Sur l’écran SMS : le panneau inline appelle **prepare** → affichage **AppOtpInput** (6 cases).
4. Saisir **`111111`** → appel **`/api/2fa/verify`** avec le jeton court puis **`interaction/complete`**.
5. Le flux enchaîne **next** vers l’écran suivant (ex. écran « post SMS »).
6. Terminer la session si le flow l’exige (**complete**) pour déclencher la **projection**.

## Résultats attendus

- **API** : `prepare` retourne `challenge_id`, `otp_token` ; avec exposition, `dev_code: "111111"`.
- **Session** (données collectées) : `phone_verified` = true, `phone_verified_at` renseigné, `phone_verification_channel` = `sms`.
- **Personne** (après `complete`) : `profile_json.compliance.phone_verified`, `phone_verified_at`, `phone_verification_channel` alignés ; `collected.phone_number` = numéro saisi.
- **Logs** : ligne `fake_sms_provider` (JSON) si `FAKE_SMS_PROVIDER` ; **aucun** appel HTTP Twilio.

## Test automatisé backend

```bash
cd services/arquantix/api
pytest tests/test_registration_phone_verification_e2e.py -vv
```

Ce test enchaîne start → submit téléphone → prepare → verify `111111` → complete → next → complete session, sans mock sur la génération OTP et avec garde `httpx` non utilisé pour Twilio.
