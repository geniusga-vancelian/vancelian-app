# PR B — Device binding (refresh / session)

## 1. Audit (état avant PR B)

### Où vivait `device_id`

| Zone | Détail |
|------|--------|
| **`auth_sessions.device_id`** | `VARCHAR(128) NOT NULL` — toujours renseigné (y compris via le sentinelle `legacy-unknown`). |
| **JWT refresh** | Claims `device_id` (+ `sid`, `jti`, …). Pas de claim `did` dédié avant PR B. |
| **En-tête HTTP** | `X-Device-ID` sur `/auth/login`, `/auth/refresh`, `/auth/revoke`, et dépendances `get_current_user`. |
| **Clients** | Flutter : `DeviceIdService.getOrCreate()` + `X-Device-ID` sur les appels session (voir `session_api.dart`, passkeys, etc.). |

### Comportement historique

- **Login** : `normalize_device_id(header)` → sans en-tête : `legacy-unknown`. Sinon troncature 128 chars.
- **Refresh** : comparaison stricte `session.device_id` vs en-tête normalisé ; **401 sans révocation** en cas de mismatch.
- **JWT** : si `device_id` dans le token ≠ en-tête → 401 (sans révocation session).
- **Fiabilité** : l’identifiant est un **indice client** (spoofable par tout possesseur de headers) ; pas de matériel cryptographique côté device_id seul.

### Limites identifiées

- Pas de claim `did` explicite ; pas d’alignement documenté « JWT ↔ session » pour la migration.
- Mismatch device : refus mais **session toujours valide** → risque de réutilisation du refresh depuis le « bon » device sans signal fort côté serveur.
- Sessions `legacy-unknown` : refresh avec un autre en-tête réel était **refusé** au lieu d’être migré.

---

## 2. Design cible (implémenté)

### Jeton refresh

- Claims **`did`** et **`device_id`** : **même valeur** (nouvelles émissions).
- **`sid`** inchangé (PR A).

### Appareil effectif (`effective_device`)

Règle unique :

1. Si l’en-tête **n’est pas** `legacy-unknown` → **`effective_device` = en-tête** (normalisé).
2. Sinon → premier disponible parmi `did`, `did`/`device_id` dans le JWT ; sinon **`legacy-unknown`**.

### A. Sémantique `srvtmp-*` (bootstrap serveur)

| Question | Réponse |
|----------|---------|
| **Placeholder définitif ?** | Non : c’est un **bootstrap** tant que le client n’a pas envoyé d’ID stable. |
| **Promotion vers un vrai device ?** | **Oui, une seule fois** : si `session.device_id` commence par `srvtmp-` et le premier refresh (ou revoke) présente un **ID client réel** (ni `legacy-unknown`, ni autre `srvtmp-*`) avec en-tête et JWT cohérents avec la session bootstrap, la ligne session est **mise à jour** vers cet ID. |
| **Après promotion** | Binding **strict** : tout autre appareil → conflit / révocation comme pour une session classique. |
| **Événement log** | `device_binding_migrated` avec `kind: srvtmp_promoted_to_client` (vs `legacy_unknown_to_client` pour `legacy-unknown`). |

### B. Matrice de décision (refresh, session trouvée)

**Légende** : *H* = `X-Device-ID` normalisé ; *J* = `did` ou `device_id` dans le JWT (normalisé) ; *S* = `auth_sessions.device_id` ; *E* = `effective_device` (voir ci‑dessus).

| H | J (dans le JWT du refresh) | S (session) | Ordre des contrôles | Action |
|---|----------------------------|-------------|---------------------|--------|
| réel A | absent ou `legacy-unknown` | * | E = A | Puis comparer S à E (voir lignes suivantes). |
| `legacy-unknown` | réel B | * | E = B | Idem. |
| `legacy-unknown` | `legacy-unknown` | * | E = `legacy-unknown` | Idem. |
| réel A | réel B, A ≠ B | * | — | **Exception** si promotion srvtmp : J est `srvtmp-*` et H est un ID client réel (pas un autre srvtmp) → **pas** de conflit jwt/header ; sinon **révocation** `device_jwt_header_conflict`. |
| * | * (J incohérent : `did` ≠ `device_id`) | * | — | 401, pas de session (claims JWT invalides). |

**Après calcul de E** (`_apply_pr_b_device_binding`) :

| S | E | Action |
|---|---|--------|
| `legacy-unknown` | réel (≠ `legacy-unknown`) | **Migration** unique vers E ; log `kind: legacy_unknown_to_client`. |
| `srvtmp-*` | réel, ≠ S, et E n’est ni `legacy-unknown` ni `srvtmp-*` | **Promotion** unique ; log `kind: srvtmp_promoted_to_client`. |
| `srvtmp-*` | autre `srvtmp-*` (≠ S) | **Révocation** (deux placeholders différents). |
| réel | réel ≠ S | **Révocation** `device_binding_mismatch`. |
| = E | = E | OK (rotation PR A ensuite). |

**Cas reviewer (numérotation)** :

1. H réel + J réel + égaux → OK (pas de branche conflit ; puis S vs E).
2. H réel + J réel + différents → révocation **sauf** promotion srvtmp (J = srvtmp, H = client réel).
3. H absent (`legacy-unknown`) + J réel → E = J ; OK si aligné S.
4. H réel + J `legacy-unknown` → E = H ; migration si S était `legacy-unknown`, promotion si S `srvtmp-*`, sinon bind.
5. H absent + J `legacy-unknown` → E = `legacy-unknown` ; tolérance legacy.
6. **`srvtmp-*`** : traité comme S ou J ; promotion possible **une fois** vers un ID client réel ; ensuite comme n’importe quelle session liée.

### Normalisation (128 caractères)

Tous les chemins passent par **`normalize_device_id`** (login, refresh, revoke, comparaisons JWT) : trim, troncature à 128, sentinelle `legacy-unknown` si vide.

### Clients mobiles (Flutter / etc.)

- Si le client a déjà un **ID stable** (`DeviceIdService`), il doit l’envoyer en **`X-Device-ID`** dès le **login** : la session est alors liée à cet ID, **sans** passer par `srvtmp-*`.
- Le champ **`device_id`** dans la réponse JSON du login lorsque le serveur a émis un **`srvtmp-*`** sert à **réconcilier** les clients sans en-tête : ils peuvent **persister** cette valeur et l’envoyer en en-tête aux appels suivants **ou** laisser le JWT porter le bootstrap jusqu’à la première promotion ; **ne pas** mélanger arbitrairement deux identités sans politique produit claire.

### Login sans en-tête

- Génération **`srvtmp-{uuid}`** côté serveur, stockée en session et dans les JWT ; champ **`device_id`** optionnel dans la réponse `Token`.

### Révocation

- **`perform_revoke`** : même **`effective_device`** ; même **exception** conflit claim/en-tête pour promotion srvtmp ; **`_session_matches_effective_for_revoke`** accepte session `srvtmp-*` + JWT encore `srvtmp-*` + en-tête = futur ID client stable.

---

## 3. Flux refresh (résumé)

```
decode JWT → cohérence did/device_id
→ header_device, effective_device
→ session par jti
→ [session] expiration
→ [session] conflit jwt vs header (sauf promotion srvtmp) → revoke
→ [session] bind (legacy / srvtmp → client, ou mismatch → revoke)
→ … claim jti, rotation PR A …
→ [pas de session] stale / sid mismatch / legacy phase 1
```

---

## 4. Fichiers modifiés

- `auth.py` — `did` dans `create_refresh_token`.
- `schemas.py` — `Token.device_id` optionnel.
- `services/auth/refresh_session.py` — helpers PR B, `issue_fresh_auth_session` (`srvtmp`), `perform_refresh`, `perform_revoke`, `_issue_pair_for_session_row`.
- `main.py` — docstring route revoke.
- `tests/test_auth_refresh.py`, `tests/test_auth_hardening_patch.py`.

---

## 5. Risques / réponses aux challenges

| Question | Réponse |
|----------|---------|
| **device_id spoofable ?** | Oui — secret partagé dans headers/JWT signés ; pas d’attestation matérielle dans cette PR. |
| **mismatch non bloquant ?** | Non — conflit fort ou binding incorrect → **révocation** (sauf promotion srvtmp contrôlée). |
| **srvtmp définitif ?** | **Non** — **une promotion** vers un ID client réel autorisée ; ensuite binding strict. |
| **refresh sans did trop longtemps ?** | Phase 1 : branche legacy ; nouvelles émissions : `did` + `device_id`. |
| **multi-device réel ?** | Une session = un appareil lié après migration/promotion ; autre appareil = autre login ou révocation. |

---

## 6. Tests

Voir `tests/test_auth_refresh.py` : `test_srvtmp_session_promotes_to_client_device_once`, migration `legacy-unknown`, conflit jwt/header, `did`, etc.

---

## 7. Monitoring recommandé (ops / sécurité)

À suivre dans les agrégateurs de logs (filtre sur `event` ou champ équivalent) :

| Événement | Intérêt |
|-----------|---------|
| **`device_binding_migrated`** | Migrations `legacy-unknown` / promotions `srvtmp-*` — volume anormal = clients sans header ou parcours bootstrap ; utile pour la **qualité** des intégrations et les régressions client. |
| **`device_mismatch_detected`** | Conflit JWT vs en-tête ou binding session — peut indiquer **tentatives d’abus**, tokens rejoués depuis un autre contexte, ou **bugs** (double envoi d’ID, mauvaise persistance mobile). |

En pratique : alertes sur taux ou spikes de `device_mismatch_detected` par route ; tableaux de bord sur le `kind` / `reason` lorsqu’ils sont présents dans les champs structurés.

---

## 8. Client mobile — discipline `device_id` (Flutter)

Implémentation de référence : `mobile/lib/features/security/passcode/data/device_id_service.dart`.

**Règles** :

- Un seul identifiant **stable par installation** : stocké en **FlutterSecureStorage** (Keychain iOS, Keystore Android), clé `SessionStorageKeys.deviceId`.
- **`getOrCreate()`** : renvoie toujours la valeur existante si présente — **pas de régénération** au redémarrage de l’app ni après reboot OS tant que les données persistées existent.
- Nouvel UUID uniquement en **premier lancement** ou après **perte** des données (désinstallation, effacement données app, etc.).
- Toutes les requêtes auth (login, refresh, revoke, etc.) doivent envoyer cet ID en **`X-Device-ID`** via les appels existants (`session_api`, passkeys, …).

Ne **pas** substituer aléatoirement l’ID serveur (`srvtmp-*` dans la réponse JSON login) à l’ID local stable : si le client a déjà un `DeviceIdService`, l’utiliser en en-tête dès le login pour éviter le bootstrap `srvtmp-*`.
