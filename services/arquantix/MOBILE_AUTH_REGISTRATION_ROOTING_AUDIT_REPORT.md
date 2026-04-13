# Audit mobile auth — login, inscription, rooting Flutter & backend

**Date** : 2026-04-07  
**Périmètre** : application mobile Arquantix (`services/arquantix/mobile`) + API FastAPI (`services/arquantix/api`), rail **SMS OTP** (connexion + inscription).

---

## 1. Synthèse exécutive

### 1.1 Symptôme « numéro fantôme »

Après suppression des **clients portfolio** (`pe_clients`), un numéro peut rester **indisponible à l’inscription** car la définition produit « client supprimé » ne recouvre pas toutes les tables d’identité. Les causes **documentées et traitées dans le code** :

| Source | Effet |
|--------|--------|
| `admin_users.mobile_e164` **UNIQUE** + ligne restante (souvent seed / admin web avec mobile) | L’inscription voit le numéro comme pris **avant** toute notion de `pe_clients`. |
| `admin_users` avec `person_id` renseigné (compte app / inscription partielle) | Bloque légitimement l’inscription — utiliser « Me connecter ». |
| `persons.profile_json->collected->phone_e164` sans cohérence avec un nouvel utilisateur | Le flux signup **réutilise** une `Person` existante ou refuse si un `AdminUser` est déjà lié (voir §4). |
| `auth_mobile_login_otp_challenges` | TTL + resend ; rarement la cause d’un blocage durable (lignes expirables). |

**Contrainte d’unicité critique** : `admin_users.mobile_e164` est **unique** au niveau SQL — toute ligne résiduelle avec ce numéro empêche une seconde ligne.

### 1.2 Correctifs déjà appliqués (backend)

- **`account_policy.app_signup_phone_blocked_by_existing_user`** : ne bloque pas l’inscription si le seul occupant est un **admin web-only** (`mobile_app_allowed=False`, `person_id` NULL) ; libération du mobile à la vérif signup (`signup_mobile_routes`).
- **`purge_mobile_auth_users.py`** : script opérationnel pour environnements vides de clients (voir §7).

### 1.3 Règle canonique implémentée (post-OTP + ACK passcode)

| Élément | Comportement |
|---------|----------------|
| **État « partiel »** | `otp_verified_but_not_secured` : JWT avec claim **`sec_inc: true`** tant que `persons.profile_json.security.local_passcode_registered_at` est absent (compte app mobile avec `person_id`). |
| **OTP SMS** (signup + login) + **passkeys** login | `issue_fresh_auth_session` : **pas** de `PeClient` obligatoire ni `APP_JWT_REQUIRES_CUSTOMER` tant que la session est partielle ; claim `sec_inc` dans l’access token. |
| **Session complète** | `POST /auth/security/local-passcode-ack` : enregistre l’horodatage serveur puis **réémet** une paire **access + refresh** **sans** `sec_inc`, avec provisionnement `PeClient` comme avant. |
| **`/api/app/*`** | `mobile_identity` : **403** `needs_security_setup` si passcode serveur manquant (JWT partiel ou Person sans ACK), **avant** lazy `PeClient`. |
| **Refresh** | Même règle : tokens renouvelés avec ou sans `sec_inc` selon la présence de l’ACK sur la `Person`. |

**Migration données** : comptes existants sans horodatage serveur doivent **repasser** par l’ACK (déverrouillage PIN ou setup PIN) ; le client Flutter appelle désormais l’ACK après déverrouillage et stocke les nouveaux jetons.

---

## 2. Cartographie Flutter (rooting)

### 2.1 Entrée utilisateur (non connecté)

| Élément | Rôle |
|---------|------|
| `WelcomeLandingScreen` (Login0) | Hero + CTA ; « Créer un compte » → `LoginPhoneScreen(signUpMode: true)` |
| `LoginPhoneScreen` | `signUpMode: true` → `POST /auth/signup/sms/start` ; sinon `POST /auth/login/sms/start` + `LoginOrchestratorResult` |
| `LoginOtpScreen` | `signupSmsVerify` **ou** `mobileLoginVerify` selon `signUpMode` ; stockage tokens → `PostLoginLocalSecurityFlow` |
| `PostLoginLocalSecurityFlow` | Si pas de PIN local → `passcodeSetupBootstrap` ; sinon flag EU registration ou `AppEntryBootstrap` |
| `PasscodeSetupScreen` (bootstrap) | Passcode local ; consommation `pendingEuRegistrationAfterPasscode` |
| `RegistrationFlowScreen` | Moteur EU (sessions registration côté API) |

### 2.2 Rails concurrents (constat)

| Rail | Usage |
|------|--------|
| SMS OTP signup | `/auth/signup/sms/*` — **création** `Person` + `AdminUser` |
| SMS OTP login | `/auth/login/sms/*` (+ alias historiques) — utilisateur **existant** |
| Passkeys / auto-login | `LoginAutoAuthScreen`, orchestrateur adaptive — **parallèle** au OTP, pas un troisième magasin d’identité |
| Admin e-mail OTP | `/auth/login/email-otp/*` — **réservé back-office / step-up**, pas le parcours mobile grand public documenté ici |

**Conclusion rooting** : le flux principal mobile est **déjà** centré sur `LoginPhoneScreen` → `LoginOtpScreen` → sécurité locale. Les variantes passkey sont des **branches** du même login SMS, pas des bases de données séparées.

---

## 3. Cartographie backend & tables

### 3.1 Endpoints clés

| Endpoint | Rôle |
|----------|------|
| `POST /auth/signup/sms/start` | Challenge OTP inscription ; vérifie occupation `admin_users` + politique |
| `POST /auth/signup/sms/verify` | Valide OTP, crée ou rattache `Person` / `AdminUser`, émet JWT |
| `POST /auth/login/sms/start` | Challenge OTP connexion ; masque comptes web-only comme inconnu |
| `POST /auth/login/sms/verify` | JWT si OTP valide |
| `POST /auth/refresh` | Si passcode ACK présent : `PeClient` + customer ; sinon session partielle (`sec_inc`). |
| `POST /auth/security/local-passcode-ack` | Écrit `local_passcode_registered_at` + **réémission JWT complète** (`access_token`, `refresh_token`). |
| `/api/app/*` | `mobile_app_client` : refus **403** `needs_security_setup` tant que setup incomplet ; sinon résolution `PeClient` (+ lazy ensure). |

### 3.2 Tableau entités métier (demandé)

| Entité | Créée quand | Supprimée / purgée quand | Sert au login ? | Sert à l’inscription ? |
|--------|-------------|--------------------------|-----------------|-------------------------|
| **Person** | Signup SMS verify ; registration engine ; scripts | Purges manuelles / cascades selon script | Indirectement (gel `login_frozen`, profil) | Oui (profil EU, `phone_e164` dans `collected`) |
| **AdminUser** | Signup verify (e-mail `@signup.internal`), seeds admin | `purge_mobile_auth_users`, suppressions admin | Oui (JWT `sub` = email) | Occupation **`mobile_e164` UNIQUE** |
| **PeClient** (`pe_clients`) | `ensure_pe_client_for_login_user` à session ; créations métier | Suppression client admin / scripts | Requis pour **`/api/app/*`** après résolution JWT | Non comme préalable au 1er OTP |
| **AuthSession** | `issue_fresh_auth_session` | Révocation, expiration | Refresh token | Non |
| **AuthMobileLoginOtpChallenge** | Start signup/login | Expiration / succès verify | Non | Stockage challenge OTP par numéro |
| **RegistrationSession** | `POST /api/registration/sessions/start` | Progression / abandon | Non direct | Oui (parcours EU) |

### 3.3 « Un vrai customer loggable » en base (état actuel)

En pratique **après la livraison §11** :

1. Après **OTP** (ou passkey sans ACK serveur) : JWT **partiel** (`sec_inc`), **sans** accès `/api/app/*` tant que le passcode n’est pas enregistré côté serveur.
2. Après **`POST /auth/security/local-passcode-ack`** : JWT **complet**, `PeClient` provisionné à l’émission de session comme avant.
3. **Passcode** : toujours saisi localement ; l’**ACK** serveur est **obligatoire** pour l’accès « customer » API.

---

## 4. Cause racine — numéro fantôme (détail)

1. **`admin_users.mobile_e164`** : index unique — toute ligne non nettoyée bloque une nouvelle inscription.
2. **Confusion `PeClient` vs identité auth** : supprimer uniquement `pe_clients` **ne supprime pas** `Person` ni `AdminUser`.
3. **Admin seed** : peut avoir un mobile sans `Person` ; avant la politique « web-only », cela bloquait comme un doublon client.
4. **`persons` orpheline avec `collected.phone_e164`** : le signup tente de **réutiliser** la personne ; si un `AdminUser` existe déjà pour cette personne → **403** inscription.

---

## 5. Règle canonique **retenue pour ce dépôt**

1. **Inscription** : numéro « pris » ssi `app_signup_phone_blocked_by_existing_user` est vrai **ou** personne gelée **ou** profil existant déjà lié à un autre utilisateur.
2. **Connexion mobile** : refus explicite des comptes **web-only** au login SMS (comportement « numéro inconnu »).
3. **Session app** : **JWT partiel** après OTP tant que pas d’ACK ; **JWT complet** + `PeClient` après ACK (voir `security_setup_state` + `refresh_session`).

---

## 6. Correctifs appliqués (référence code)

| Fichier | Changement |
|---------|------------|
| `api/services/auth/account_policy.py` | Distinction blocage signup : Person liée vs admin web-only |
| `api/services/auth/signup_mobile_routes.py` | Doc module + libération mobile sur admin web-only à la vérif |
| `api/scripts/purge_mobile_auth_users.py` | Purge ciblée comptes mobile + données liées |
| `api/services/auth/security_setup_state.py` | État ACK + session partielle |
| `api/services/auth/refresh_session.py` | `sec_inc` + skip PeClient si partiel |
| `api/services/auth/local_passcode_ack_routes.py` | ACK + réémission tokens |
| `api/services/test_clients/mobile_identity.py` | Garde `needs_security_setup` |
| `mobile/.../session_api.dart` & écrans passcode | ACK await + stockage jetons |

---

## 7. Requêtes SQL de diagnostic (ops)

```sql
-- Occupation directe auth (cause #1 fantôme)
SELECT id, email, mobile_e164, person_id, mobile_app_allowed
FROM admin_users
WHERE mobile_e164 IS NOT NULL
ORDER BY id;

-- Personnes avec mobile collecté en profil (signup réutilise ou bloque)
SELECT id, login_frozen,
       profile_json->'collected'->>'phone_e164' AS phone_e164
FROM persons
WHERE (profile_json->'collected'->>'phone_e164') IS NOT NULL;

-- Clients portfolio restants
SELECT id, email, person_id FROM pe_clients;
```

---

## 8. Tests ajoutés / couverts

- `api/tests/test_signup_mobile_sms.py` : JWT avec `sec_inc` après inscription OTP ; cas réutilisation / web-only / doublon.
- `api/tests/test_mobile_identity_security.py` : `403 needs_security_setup` sur `/api/app/bootstrap` si JWT partiel ; lazy `PeClient` avec `local_passcode_registered_at` sur la `Person`.
- `api/tests/test_local_passcode_ack.py` : réponse ACK + `access_token` / `refresh_token` sans `sec_inc`.
- `api/tests/test_auth_refresh.py` : login / refresh inchangés pour utilisateurs avec ACK (fixtures `make_admin_user_with_pe_client`).

Commande : `pytest services/arquantix/api/tests/test_signup_mobile_sms.py tests/test_mobile_identity_security.py tests/test_local_passcode_ack.py tests/test_auth_refresh.py -q`

---

## 9. Limites restantes & cleanup futur

- **Passkeys** : rail parallèle au SMS ; même règle `sec_inc` si pas d’ACK serveur.
- **`admin@local.dev`** : bootstrap dev dans `auth.py` — ne doit pas exister en production.
- **Scripts** : `purge_all_customers.py` / `repair_sms_signup_duplicate_phone.py` — à utiliser avec précaution ; préférer `purge_mobile_auth_users.py` pour un reset auth mobile ciblé.

---

## 10. Références fichiers clés

| Zone | Fichiers |
|------|----------|
| Politique compte | `api/services/auth/account_policy.py` |
| Signup SMS | `api/services/auth/signup_mobile_routes.py` |
| Login SMS | `api/services/auth/mobile_otp_login_routes.py` |
| Session + PeClient | `api/services/auth/refresh_session.py`, `api/services/client_identity/service.py` |
| JWT → PeClient | `api/services/test_clients/mobile_identity.py` |
| État passcode | `api/services/auth/security_setup_state.py` |
| Flutter post-login | `mobile/lib/features/app_entry/application/post_login_local_security_flow.dart` |
| Orchestration login | `mobile/lib/features/auth/orchestrator/login_orchestrator.dart` |

---

## 11. Implémentation « JWT plein accès après passcode » (2026)

### Fichiers principaux

| Fichier | Rôle |
|---------|------|
| `api/services/auth/security_setup_state.py` | `person_has_local_passcode_ack`, `should_issue_partial_session_for_mobile_app`, détail `needs_security_setup` |
| `api/auth.py` | `create_access_token(..., security_incomplete=...)` → claim `sec_inc` |
| `api/services/auth/refresh_session.py` | Session partielle vs complète ; refresh aligné |
| `api/services/auth/local_passcode_ack_routes.py` | ACK + `issue_fresh_auth_session` (tokens dans le corps) |
| `api/services/test_clients/mobile_identity.py` | Garde `/api/app/*` |
| `mobile/.../session_api.dart` | Persistance des jetons retournés par l’ACK |
| `mobile/.../passcode_setup_screen.dart` | `await` sur l’ACK |
| `mobile/.../passcode_unlock_screen.dart` | ACK après déverrouillage PIN pour synchroniser le serveur |

### Plan de migration production

1. Déployer API + application mobile **ensemble** (réponse ACK enrichie).
2. Utilisateurs avec session ancienne : au prochain déverrouillage ou création PIN, **ACK** → jetons complets.
3. Optionnel : script SQL de **backfill** `local_passcode_registered_at` pour comptes déjà validés manuellement (hors scope code).

### Limites

- **Admin / e-mail OTP** : chemins hors « app mobile customer » restent soumis aux règles existantes (`enforce_access_security`, comptes sans `Person`).
- **Numéro fantôme** : inchangé côté `admin_users.mobile_e164` UNIQUE + politiques `account_policy` ; purger avec `purge_mobile_auth_users.py` si besoin.

---

## 12. États compte `PARTIAL` / `ACTIVE` + orphelins (2026)

### Définition (backend)

| État | Condition |
|------|-----------|
| **PARTIAL** | Person liée app (`mobile_app_allowed`) mais pas **ACTIVE** : passcode serveur manquant **ou** **PeClient** absent. |
| **ACTIVE** | `local_passcode_registered_at` **et** ligne `pe_clients` pour la Person. |
| **INCOMPLETE** | `admin_users` sans `person_id` (orphelin résiduel). |
| **ADMIN_WEB** | Compte web-only (`mobile_app_allowed=False` / e-mail admin). |

- **JWT** : claim **`acct_st`** (alias `PARTIAL` / `ACTIVE` / …), en plus de **`sec_inc`** tant que le compte n’est pas ACTIVE.
- **Login SMS** (`POST /auth/login/sms/start`) : champs **`account_state`** et **`resume_registration_hint`** (`true` si ≠ ACTIVE) pour orienter le client vers la finalisation du flux.
- **Inscription** : si le numéro est déjà sur un compte **PARTIAL** → **403** `signup_phone_use_login` + `account_state` ; si **ACTIVE** → `signup_phone_unavailable`.

### Orphelins (sans `person_id`)

- **Politique** : `app_signup_phone_blocked_by_existing_user` est **faux** pour `person_id` NULL (hors web-only) — l’inscription peut envoyer un OTP ; à la **vérif**, le mobile est libéré sur la ligne résiduelle (comme pour le web-only).
- **Script** : `api/scripts/reconcile_orphan_mobile_accounts.py` (`--dry-run` / `--apply`) pour lister ou effacer les `mobile_e164` orphelins en prod.

### Provisionnement PeClient

- Avant **dérivation** ACTIVE et **JWT** complet : si passcode ACK présent, **`ensure_pe_client`** est appelé dans `issue_fresh_auth_session` et sur le chemin bootstrap `/api/app/*` (`ensure_pe_client_if_passcode_ack`).

### Colonne SQL `persons.account_state` (migration **129**)

- **Persistance** : `PARTIAL` / `ACTIVE` (nullable pour lignes hors périmètre app ou legacy non classés).
- **Source de vérité métier** : inchangée — `derive_account_state` reste basé sur **facts** (`local_passcode_registered_at` + `pe_clients`). La colonne est **alignée** à chaque `issue_fresh_auth_session` via `persist_person_account_state_column`.
- **Inscription** : nouvelle `Person` créée avec `account_state = PARTIAL` dès la vérif OTP.
- **Backfill Alembic** :
  - `ACTIVE` si `pe_clients` + horodatage passcode dans `profile_json.security`.
  - `PARTIAL` sinon pour les `persons` liées à un `admin_users` app (`mobile_app_allowed`, e-mail `@signup.internal` ou `mobile_e164` renseigné).

---

## 13. Stratégie de migration production (résumé)

1. **Déployer** la migration **129** avant ou avec le déploiement API (fenêtre de maintenance courte si volumétrie importante).
2. **Comptes déjà cohérents** (passcode + PeClient) : le backfill les marque **`ACTIVE`** ; les incomplets **`PARTIAL`**.
3. **Post-déploiement** : toute nouvelle session met à jour la colonne ; pas d’action mobile obligatoire.
4. **Orphelins** : continuer à utiliser `reconcile_orphan_mobile_accounts.py` ; la colonne ne remplace pas ce nettoyage.
5. **Requêtes / BI** : filtrer sur `persons.account_state` pour cohortes ; pour l’**autorisation**, s’appuyer toujours sur JWT (`acct_st`, `sec_inc`) et garde `/api/app/*`.

---

## 14. Flutter — alignement PARTIAL / ACTIVE (2026)

### Source de vérité UX (sans remplacer la sécurité serveur)

| Signal | Origine | Usage Flutter |
|--------|---------|----------------|
| `sms_otp_dispatched` | `POST /auth/login/sms/start` | Si `false` : numéro **non** éligible SMS login → modale « Créer un compte » / autre méthode (pas d’écran OTP trompeur). |
| `account_state`, `resume_registration_hint` | Même réponse | Titres / sous-texte OTP : **PARTIAL** → « Finalisez votre inscription » (pas « login complet »). |
| `acct_st`, `sec_inc` | JWT access après verify / refresh | `isAccessTokenAccountActiveForApp()` : **ACTIVE** et pas `sec_inc` → compte exploitable pour flux « post-login » ; sinon reprise inscription après PIN. |

### Routage après OTP (connexion, pas inscription)

1. Stockage des jetons puis **`PostLoginLocalSecurityFlow.flagRegistrationResumeIfAccountNotActive()`** : si JWT ≠ ACTIVE → même drapeau que l’inscription mobile (`pending_eu_reg_after_passcode`) → après **PIN local** → **`RegistrationFlowScreen`** (reprise).
2. Si JWT **ACTIVE** → comportement existant : PIN setup / déverrouillage → **Home** (shell).

### Garde flux trading (wallet)

- **`TradingFlowSessionGuard.ensureSessionOrPrompt`** : exige en plus **`isLastStoredAccessAccountActive()`** — pas d’accès achat/vente avec session **PARTIAL** (message : finaliser l’inscription).

### Fichiers Flutter principaux

- `login_phone_screen.dart` — `sms_otp_dispatched`, modale inscription.
- `login_otp_screen.dart` — titres PARTIAL, branchement `flagRegistrationResumeIfAccountNotActive` pour login.
- `login_orchestrator.dart` / `login_auto_auth_screen.dart` — passage des hints SMS ; passkey success → même flag si JWT non ACTIVE.
- `post_login_local_security_flow.dart` — `flagRegistrationResumeIfAccountNotActive`.
- `session_service.dart` — `isLastStoredAccessAccountActive()`.
- `jwt_access_claims.dart` — `jwtExtractAccountState`, `jwtExtractSecurityIncomplete`, `isAccessTokenAccountActiveForApp`.
- `session_security_snapshot.dart` — persistance `acct_st` / `sec_inc` dans le snapshot sécurité.
- `trading_flow_session_guard.dart` — garde ACTIVE pour flux sensibles.

### Tests

- `mobile/test/features/security/passcode/jwt_access_claims_account_state_test.dart` — règles JWT ACTIVE / PARTIAL / legacy.

---

*Fin du rapport.*
