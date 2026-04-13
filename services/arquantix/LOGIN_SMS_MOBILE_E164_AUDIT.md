# Executive Summary

| Statut | Détail |
|--------|--------|
| **Schéma DB** | **OK** — révision Alembic **117 (head)** ; colonne `admin_users.mobile_e164` et table `auth_mobile_login_otp_challenges` présentes sur la base locale ciblée par `DATABASE_URL`. |
| **Données** | **NOK pour le login SMS réel** — sur l’instantané audité, **un seul** admin (`id=1`, `admin@arquantix.com`) avec **`mobile_e164 = NULL`**. Aucune correspondance possible avec un numéro saisi dans l’app → pas de challenge / pas d’envoi OTP (comportement anti-énumération : HTTP 200 « accepté » sans ligne en base). |
| **Flow backend** | **OK (conception)** — `POST /auth/login/sms/start` et `POST /auth/login/sms/verify` ; OTP partagé via `sms_otp_core` (dont `TWO_FACTOR_DEV_FIXED_CODE`). |
| **Action requise** | Renseigner **`mobile_e164`** en **E.164 identique** au payload envoyé par Flutter (ex. `+33651624864`), pour l’admin utilisé pour les tests. |

---

# Environment Checked

- **Répertoire API** : `services/arquantix/api`
- **Chargement des variables** : même ordre que `database.py` — `.env.local` puis `.env`
- **API HTTP** : `GET http://127.0.0.1:8000/health` → **200** au moment de l’audit (serveur local supposé déjà démarré)

---

# Database Revision

**Commande exécutée :**

```bash
cd services/arquantix/api && python3 -m alembic current
```

**Résultat :**

```text
117 (head)
```

**URL DB (masquée) affichée par Alembic :** `postgresql://arquantix:***@localhost:5443/arquantix`

---

# Colonne et table (information_schema)

**Vérifications SQL exécutées via SQLAlchemy sur `DATABASE_URL` :**

- Colonne `public.admin_users.mobile_e164` : **existe** (`character varying`, nullable **YES**).
- Table `public.auth_mobile_login_otp_challenges` : **existe**.

---

# API → PostgreSQL

| Paramètre | Valeur (audit) |
|-----------|----------------|
| Host | `localhost` |
| Port | `5443` |
| Database | `arquantix` |
| User | `arquantix` |

Source : `DATABASE_URL` après `load_dotenv(.env.local)` puis `load_dotenv(.env)`.

---

# Variables d’environnement (chargement Python hors processus uvicorn)

**Commande :** script Python `load_dotenv` depuis `api/` (voir audit session).

**Résultats observés sur l’environnement d’exécution de l’audit :**

| Variable | Valeur lue |
|----------|------------|
| `AUTH_MOBILE_OTP_LOGIN_ENABLED` | `true` |
| `TWO_FACTOR_DEV_FIXED_CODE` | `111111` |
| `TWO_FACTOR_DEV_EXPOSE_CODE` | non défini *(le fichier `.env` versionné dans le dépôt peut contenir `true` — vérifier fichier sur disque et redémarrage API)* |
| `APP_ENV` | non défini *(idem — si absent au runtime, `two_factor_env.effective_app_env()` peut rester vide ; en dev local l’absence de `production`/`staging` évite souvent le blocage du code fixe)* |

**Recommandation :** confirmer avec le processus réel de l’API :

```bash
# Depuis un shell où l’API a été lancée, ou en ajoutant un endpoint debug interdit en prod :
# Vérifier que uvicorn a bien rechargé le .env après modification.
```

---

# Admin Users Audit

**Requête exécutée :**

```sql
SELECT id, email, mobile_e164 FROM admin_users ORDER BY id;
```

**Résultat (instantané audit) :**

| id | email | mobile_e164 |
|----|-------|-------------|
| 1 | admin@arquantix.com | `NULL` |

**Interprétation :** un seul compte ; pas d’« arbitrage » entre plusieurs admins. **Aucun** admin n’a de mobile renseigné → **login SMS ne peut pas aboutir** tant que `mobile_e164` n’est pas défini pour ce compte (ou un autre compte créé plus tard).

---

# mobile_e164 Findings

| Critère | État |
|---------|------|
| NULL | **Oui** pour `id=1` |
| Vide string | Non (NULL) |
| E.164 | N/A tant que NULL |

---

# Login SMS Flow Audit

## Endpoints

| Étape | Méthode | Chemin canonique | Alias |
|-------|---------|------------------|--------|
| Start | `POST` | `/auth/login/sms/start` | `/auth/login/start` |
| Verify | `POST` | `/auth/login/sms/verify` | `/auth/login/verify` |

Préfixe routeur : `/auth` → URLs complètes ci-dessus.

## Start — payload

- **Body JSON :** `{ "phone": "<string>" }` (E.164 recommandé, ex. `+33651624864`).
- **Normalisation serveur :** espaces supprimés ; si pas de `+` au début, un `+` est ajouté (`mobile_otp_login_routes._normalize_phone_e164`).
- **Pas de champ `purpose`** dans ce flux (hors modèle 2FA `/api/2fa`).
- **Headers :** `X-Device-ID` optionnel pour l’audit ; pas requis pour le start.

## Verify — payload

- **Body JSON :** `{ "phone": "<même E.164 normalisé>", "code": "<6 chiffres>" }`
- **Pas de `challenge_id` côté client** : le serveur retrouve la ligne dans `auth_mobile_login_otp_challenges` par `phone_e164_normalized`.
- **Headers :** `X-Device-ID` recommandé (session / device binding).
- **Réponse succès :** JSON avec notamment `access_token` et `refresh_token` (via `issue_fresh_auth_session`).

## Réutilisation moteur OTP

- **Code OTP :** `services/security/sms_otp_core.py` (`new_plaintext_sms_otp`, `hash_sms_otp`, `verify_sms_otp`) — aligné 2FA / registration.
- **Envoi SMS :** `get_sms_provider()` ; en **relaxed** + provider **noop** → `FakeSmsProvider` (dev).
- **Code fixe dev :** `TWO_FACTOR_DEV_FIXED_CODE` (ex. `111111`) utilisé à la génération du plaintext.
- **Délai renvoi :** `RESEND_SECONDS` (30 s) entre deux starts pour un même numéro connu.
- **Audit / masking :** événements `_auth_audit` ; affichage masqué côté réponse `masked_target`.

---

# E.164 Normalization Check

## Flutter (écran login téléphone)

Fichier : `mobile/lib/core/phone_e164.dart` — fonction `normalizePhoneFieldToE164(rawNational, dialCode)` :

- Nettoie espaces, points, tirets, parenthèses.
- Si la saisie commence déjà par `+`, elle est renvoyée telle quelle (hors trim interne).
- Si la partie nationale commence par `0`, le `0` est retiré avant concaténation avec l’indicatif.
- L’indicatif est normalisé avec `+` si besoin.

**Exemple produit :**

- Saisie : `06 51 62 48 64`, pays FR → indicatif `+33`
- Résultat : **`+33651624864`**

## Backend

- Normalisation **supplémentaire** légère : retire les espaces, garantit un préfixe `+`.

## Correspondance DB

**La valeur dans `admin_users.mobile_e164` doit être strictement égale** (après normalisation des deux côtés) à la chaîne envoyée dans `POST .../start` et `.../verify`, typiquement **`+33651624864`** pour l’exemple ci-dessus.

---

# Test local (HTTP)

### Cas actuel (mobile_e164 NULL)

Un `POST /auth/login/sms/start` avec un numéro quelconque **sans** admin associé renvoie **200** avec `masked_target`, mais **aucune ligne** dans `auth_mobile_login_otp_challenges` (anti-énumération).

**Exemple curl :**

```bash
curl -s -X POST http://127.0.0.1:8000/auth/login/sms/start \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+33651624864"}'
```

**Vérification challenge :**

```sql
SELECT * FROM auth_mobile_login_otp_challenges;
```

### Cas succès (après correction SQL ou script)

1. Définir `mobile_e164 = '+33651624864'` pour l’admin utilisé (même valeur que l’app).
2. Répéter le `curl` start → une ligne doit apparaître dans `auth_mobile_login_otp_challenges`.
3. Avec `TWO_FACTOR_DEV_FIXED_CODE=111111` :

```bash
curl -s -X POST http://127.0.0.1:8000/auth/login/sms/verify \
  -H 'Content-Type: application/json' \
  -H 'X-Device-ID: curl-test-device' \
  -d '{"phone":"+33651624864","code":"111111"}'
```

4. Attendu : **200** et présence de **`access_token`** dans le JSON.

*(Non exécuté automatiquement dans cet audit tant que `mobile_e164` est NULL — à lancer après correction locale.)*

---

# Local Fix Applied or Proposed

**Aucun `UPDATE` exécuté dans le cadre de la rédaction du rapport** (audit seulement).

## Option A — SQL template (à compléter)

Remplacez l’email et le numéro par **vos** valeurs cohérentes avec l’app :

```sql
-- Vérification
SELECT id, email, mobile_e164 FROM admin_users;

-- Mise à jour (exemple — à adapter)
UPDATE admin_users
SET mobile_e164 = '+33651624864'
WHERE email = 'admin@arquantix.com';

-- Re-vérification
SELECT id, email, mobile_e164 FROM admin_users WHERE email = 'admin@arquantix.com';
```

## Option B — Script Python fourni

```bash
cd services/arquantix/api
python3 scripts/local_admin_mobile_e164.py list
python3 scripts/local_admin_mobile_e164.py set --email 'admin@arquantix.com' --phone '+33651624864'
python3 scripts/local_admin_mobile_e164.py list
```

Fichier : `api/scripts/local_admin_mobile_e164.py`

---

# Test Result

| Test | Résultat |
|------|----------|
| `alembic current` | **117 (head)** |
| Colonne + table | **Présentes** |
| Liste admins | **1 ligne, `mobile_e164` NULL** |
| E2E start→verify avec tokens | **Non validé** (bloqué par `mobile_e164` NULL) |

**Preuve HTTP + DB (audit, API locale `127.0.0.1:8000`) :**

```bash
curl -s -X POST http://127.0.0.1:8000/auth/login/sms/start \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+33651624864"}'
```

Réponse observée :

```json
{"status":"accepted","masked_target":"+336 ••••••64","resend_after_seconds":30,"dev_code":null}
```

Immédiatement après : `SELECT count(*) FROM auth_mobile_login_otp_challenges` → **0** ligne.

Cela confirme le chemin **« numéro inconnu côté admin »** : HTTP 200 sans persistance de challenge, aligné avec l’anti-énumération.

**Note `dev_code` :** valeur `null` dans cette réponse — vérifier que `TWO_FACTOR_DEV_EXPOSE_CODE=true` est bien chargé par le **processus uvicorn** (fichier `.env` sauvegardé + redémarrage) si vous voulez exposer le code en JSON.

---

# Next Actions

1. **Sauvegarder** le fichier `api/.env` sur disque et **redémarrer** l’API si vous ajoutez `APP_ENV=dev` ou `TWO_FACTOR_DEV_EXPOSE_CODE` (vérifier que `python-dotenv` les voit bien).
2. **Renseigner `mobile_e164`** pour l’admin de test avec le **même E.164** que celui produit par Flutter (script ou SQL ci-dessus).
3. **Ré-exécuter** la séquence curl start → vérif table → verify avec `111111`.
4. **Tester** dans l’app mobile avec le même numéro.

---

# Commandes exécutées (audit)

```bash
cd services/arquantix/api && python3 -m alembic current
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health
```

+ script Python ponctuel : `load_dotenv`, requêtes `information_schema` et `SELECT id, email, mobile_e164 FROM admin_users`.

---

# Conclusion

- **Infrastructure (migration, tables, endpoints, normalisation E.164, moteur OTP partagé) :** cohérente avec l’objectif dev local.
- **Blocage actuel identifié de façon factuelle :** **`mobile_e164` NULL** pour le seul admin listé — **sans correction données, pas de login SMS abouti.**
- **Après** `UPDATE` / `local_admin_mobile_e164.py set` avec le bon `+33…`, le flux **start → code dev `111111` → verify → tokens** est le chemin attendu.
