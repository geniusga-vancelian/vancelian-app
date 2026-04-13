# Rapport — correctif `GET /api/app/profile` (404 JWT valide sans PeClient)

## Résumé exécutif

Le **404** avec message `No client profile linked to this session.` et le log `security_mobile: bearer_valid_but_no_pe_client` surviennent lorsque le JWT est valide mais qu’**aucune ligne `pe_clients`** ne correspond aux claims (`person_id` / `pid` / e-mail `sub`).

**Cause racine :** certains flux d’inscription (notamment **SMS**) créent `Person` + `AdminUser` **sans** créer de `PeClient`, alors que les routes `/api/app/*` ne résolvent que via **`pe_clients`**.

**Stratégie retenue :** provisionnement **idempotent** d’un `PeClient` minimal lié à l’identité JWT, à deux niveaux :

1. **Login / refresh** — `ClientIdentityService.ensure_pe_client_for_login_user` appelé en *best effort* depuis `issue_fresh_auth_session` et les chemins refresh (`services/auth/refresh_session.py`).
2. **Lazy sur résolution mobile** — si le premier `SELECT` ne trouve pas de client, `client_from_access_token` tente le même `ensure` via `AdminUser` résolu sans ambiguïté depuis le JWT (`services/test_clients/mobile_identity.py`).

Ainsi, un utilisateur mobile authentifié avec `person_id` + `AdminUser` aligné obtient un profil client **sans** repasser obligatoirement par un nouveau login.

---

## 1. Cause racine exacte

| Élément | Comportement |
|--------|----------------|
| JWT | Valide → payload avec `person_id`/`pid` et/ou `sub` (e-mail). |
| Résolution initiale | `pe_client_from_jwt_payload` : `pe_clients` par `person_id` ou par `email` si `sub` contient `@`. |
| Échec | Aucune ligne → avant correctif, **404** immédiat après décodage Bearer. |

Le trou métier : **`Person` existe**, **`AdminUser` existe**, mais **`pe_clients`** n’a jamais été créé ou lié pour cette personne (flux SMS, chemins legacy, ou ordre d’opérations).

---

## 2. Où le PeClient aurait dû être créé

- **Idéal métier :** à la **fin d’un onboarding / registration** qui matérialise une personne exploitable côté portfolio.
- **En pratique :** plusieurs chemins (SMS, web, migrations) n’appelaient pas systématiquement la création de `PeClient`.
- **Correctif :** point central **`ClientIdentityService.ensure_pe_client_for_login_user`** (`services/client_identity/service.py`) — création minimale (`status=pending`, `kyc_status` aligné sur la personne), liaison `persons.client_id`, audit `CLIENT_AUTO_PROVISIONED_LOGIN`.

---

## 3. Stratégie retenue

### 3.1 Au login / refresh

- `_ensure_pe_client_for_login_user_best_effort` dans `refresh_session.py` : avant `commit` de session, si l’utilisateur a un `person_id`, appel à `ensure_pe_client_for_login_user`.
- Couvre les **nouveaux tokens** émis après login ou refresh.

### 3.2 Lazy dans `mobile_identity`

- `_admin_user_from_mobile_jwt_payload` : même critères que la résolution PeClient (`person_id`/`pid` ou `sub` e-mail).
- `_try_ensure_pe_client_for_mobile_jwt` : si `AdminUser` + `person_id`, appelle `ensure_pe_client_for_login_user` avec `actor_type="mobile_identity.lazy_ensure"`, puis `flush` et re-query.
- **`client_from_access_token`** : si `pe_client_from_jwt_payload` est vide, tente le lazy ensure puis **re**-interroge `pe_client_from_jwt_payload`.

Toute route qui dépend de `mobile_app_client` / `resolve_bootstrap_client` bénéficie de ce mécanisme (bootstrap, profile, etc.).

### 3.3 Ce qui n’est pas fait (sécurité)

- Pas de fallback « client test » sur Bearer (inchangé : réservé au mode dev `ARQUANTIX_ALLOW_UNAUTHENTICATED_APP_ROUTES`).
- Pas de création si l’identité JWT est **ambiguë** (pas d’`AdminUser` résolu, ou pas de `person_id`).
- Si l’e-mail PeClient est déjà lié à **une autre** personne → `AlreadyLinkedError` (pas de doublon silencieux).
- Claims `client_id` / `cid` dans le JWT : vérification stricte vs client résolu (**403** si mismatch).

---

## 4. Garanties d’idempotence

- **Premier appel** : `SELECT pe_clients WHERE person_id = ?` → si absent, création sous verrou logique sur la personne (`with_for_update`), puis `person.client_id` mis à jour.
- **Appels suivants** : la ligne existe → retour immédiat de l’existant, **pas de second insert**.
- **Contrainte e-mail** : si un client existe déjà pour cet e-mail et la même personne, le chemin « déjà lié » évite les doublons ; conflit inter-personnes → erreur explicite.

---

## 5. Tests ajoutés / couverts

| Fichier | Scénario |
|---------|----------|
| `tests/test_mobile_identity_security.py` | `test_bootstrap_200_lazy_provisions_pe_client_when_missing` — bootstrap **200** après provisionnement lazy. |
| `tests/test_mobile_identity_security.py` | `test_profile_200_lazy_provisions_pe_client_when_missing` — profile **200** dans le même cas. |
| `tests/test_ensure_pe_client_login.py` | Création quand seule la personne existe ; idempotence quand déjà lié. |

À exécuter :

```bash
cd services/arquantix/api && python3 -m pytest tests/test_mobile_identity_security.py tests/test_ensure_pe_client_login.py -q
```

(Résultat vérifié : **11 passed**.)

Couverture implicite attendue par la spec :

| Cas | Statut attendu |
|-----|----------------|
| Auth + PeClient existant | **200** |
| Auth + pas de PeClient → auto-create | **200** puis second appel sans doublon |
| JWT invalide | **401** |
| `client_id`/`cid` ≠ client résolu | **403** |

---

## 6. Impact login / registration / profile

| Zone | Impact |
|------|--------|
| **Login / refresh** | Nouvelle session peut déjà attacher un PeClient avant tout appel `/api/app/*`. |
| **Registration SMS (et assimilés)** | Même sans PeClient à la création du compte, le **premier** appel authentifié à bootstrap/profile peut provisionner (lazy). |
| **Profile** | Plus de 404 « fantôme » pour les sessions avec JWT cohérent et `AdminUser` + `person_id`, sauf cas d’erreur métier (e-mail pris ailleurs, personne absente). |

---

## 7. Références code

- `services/arquantix/api/services/client_identity/service.py` — `ensure_pe_client_for_login_user`
- `services/arquantix/api/services/auth/refresh_session.py` — `_ensure_pe_client_for_login_user_best_effort`
- `services/arquantix/api/services/test_clients/mobile_identity.py` — `client_from_access_token`, `_try_ensure_pe_client_for_mobile_jwt`

Document connexe (diagnostic initial) : `API_PROFILE_404_ROOT_CAUSE_REPORT.md`.
