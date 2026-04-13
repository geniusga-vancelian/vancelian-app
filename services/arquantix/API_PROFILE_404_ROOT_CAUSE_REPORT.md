# Rapport — `GET /api/app/profile` en **404** malgré un JWT valide

## Résumé exécutif

Un **Bearer valide** prouve seulement que l’utilisateur **auth** (`AdminUser`) est authentifié.  
Les routes `/api/app/*` (bootstrap, profile, etc.) ne résolvent **pas** l’utilisateur admin : elles cherchent un enregistrement **`pe_clients`** (modèle `Client` / PeClient) à partir des claims JWT.

Si **aucune ligne PeClient** n’est liée à la `person_id` du JWT (et que l’e-mail `sub` ne permet pas non plus de retrouver un client), le backend renvoie **404** avec le message :

`No client profile linked to this session.`

Ce n’est **pas** un bug de forward BFF ni de signature JWT : c’est un **rattachement métier manquant** entre **Person** (identité onboarding / KYC) et **PeClient** (client portfolio / app mobile).

---

## 1. Résolution côté backend (fichier `mobile_identity.py`)

### Étapes

1. Décodage JWT → payload (sinon **401**).
2. **`pe_client_from_jwt_payload(db, payload)`** :
   - Si `person_id` ou `pid` dans le token → `SELECT * FROM pe_clients WHERE person_id = :pid`.
   - Sinon, si `sub` est un e-mail (`@`) → `SELECT * FROM pe_clients WHERE email = sub`.
3. Si aucun PeClient → `client_from_access_token` retourne `None`.
4. **`resolve_bootstrap_client`** avec Bearer → **404** si aucun client.

### Conséquences

- **Un PeClient doit exister** pour que `/api/app/profile` réponde **200** (avec Bearer).
- Le **JWT seul** ne suffit pas : il faut une ligne **`pe_clients`** cohérente avec `person_id` **ou** `email`.

---

## 2. Pourquoi certaines sessions « valides » n’ont pas de PeClient

### Cas principal identifié : inscription SMS (`signup_mobile_routes.py`)

Le flux **POST `/auth/signup/sms/verify`** crée :

- une **`Person`** ;
- un **`AdminUser`** avec e-mail placeholder `*.@signup.internal` et `person_id` ;

mais **ne crée pas** de ligne **`pe_clients`**.

Le JWT émis par `issue_fresh_auth_session` contient :

- `sub` = e-mail placeholder (unique) ;
- `pid` = UUID de la personne.

La résolution par `person_id` échoue **tant qu’il n’existe pas** de `pe_clients.person_id` correspondant → **404** sur `/api/app/profile`.

### Autres cas possibles (legacy / données)

- **Person** créée sans provisioning portfolio (scripts, migrations partielles).
- **AdminUser** avec `person_id` mais jamais de client trading rattaché.
- **E-mail** `sub` ≠ `pe_clients.email` (peu probable si le même email sert partout).

---

## 3. Correctif backend appliqué

### Objectif

Garantir **au moment de l’émission de session** (tokens access/refresh) qu’un **PeClient** existe pour toute authentification avec `user.person_id` renseigné.

### Implémentation

1. **`ClientIdentityService.ensure_pe_client_for_login_user`** (`services/client_identity/service.py`)  
   - Idempotent : si un PeClient existe déjà pour `person_id`, retourne.  
   - Sinon crée un `pe_clients` avec `email = user.email`, lie `persons.client_id`, aligne `kyc_status` à partir de la personne.

2. **`refresh_session.py`**  
   - **`_ensure_pe_client_for_login_user_best_effort`** : appelé depuis **`issue_fresh_auth_session`** (login / OTP / passkeys / etc.) **avant** le `commit` de la session auth.  
   - Appelé aussi sur **`/auth/refresh`** (parcours session normale + branche *legacy upgrade*) **avant** `commit`, pour les utilisateurs déjà connectés sans PeClient (données anciennes).  
   - En cas d’erreur inattendue (ex. collision d’e-mail), log **warning** — l’auth continue (comportement *best effort* ; à durcir si besoin métier).

### Tests

- `api/tests/test_ensure_pe_client_login.py` : création idempotente.

---

## 4. Validation

```bash
cd services/arquantix/api && python3 -m pytest tests/test_ensure_pe_client_login.py tests/test_mobile_identity_security.py -q
```

---

## 5. Risques / suites possibles

- **Collision d’e-mail** sur `pe_clients.email` (unique) : levée comme `AlreadyLinkedError` — loggée si l’ensure est dans un `try/except` large ; à monitorer en prod.
- **Utilisateurs sans `person_id`** (admin pur) : aucun ensure ; ils n’utilisent pas les routes `/api/app/*` avec un JWT « mobile » — comportement inchangé.
- **Renforcer** : rendre l’ensure **strict** (échec login si ensure échoue) plutôt que warning — décision produit.

---

## 6. Références code

| Fichier | Rôle |
|---------|------|
| `api/services/test_clients/mobile_identity.py` | Résolution JWT → PeClient, 404 |
| `api/services/auth/signup_mobile_routes.py` | Signup SMS sans PeClient (cause racine) |
| `api/services/auth/refresh_session.py` | `issue_fresh_auth_session` + ensure |
| `api/services/client_identity/service.py` | `ensure_pe_client_for_login_user` |
