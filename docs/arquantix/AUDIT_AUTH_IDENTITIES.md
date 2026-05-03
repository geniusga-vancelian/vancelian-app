# Audit identités & authentification — Vancelian Arquantix

> **Date :** 2026-05-02
> **Statut :** ✅ **CLÔTURÉ — Phase 2a livrée.** Toutes les 5 décisions §7
> sont implémentées (`classify_actor()` avec `SUSPENDED`, court-circuits
> ADMIN_BO 403, fix `_require_client` globalisé via
> `services/auth/client_id_resolver.py::patch_auth_client_id_from_person`,
> `user_id=1839` orphelin déféré en backlog dédié, `AuthContext.role`
> hardcodé tracé en dette technique Phase 3+).
>
> **Objectif initial :** établir une vérité partagée sur le modèle d'identité avant
> de coder Compliance V2 (qui devra décider, lire, agir au nom d'un client
> sans jamais le confondre avec un admin BO).
>
> **Documents liés :**
> - `MULTI_AGENTS.md` — architecture cible des agents
> - `MULTI_AGENTS_DATA_SOURCES.md` — cartographie data
> - `MULTI_AGENTS_RUNTIME.md` — spec runtime agentique (v1.1, Phase 2a livrée)

---

## TL;DR — 5 découvertes critiques pour Compliance V2

1. **La table `admin_users` est trompeusement nommée** — c'est en réalité
   *« le magasin technique unique des credentials d'auth »* utilisé par
   **TOUS** les utilisateurs (admins BO **ET** customers de l'app mobile).
   Le distinguo se fait via la **présence/absence** d'un `pe_clients` lié
   à la même `person_id`, pas via le nom de la table.

2. **`AuthContext.role` est hardcodé à `"admin"` dans tout le code Python.**
   Le helper `is_admin` retourne donc `True` pour tout JWT valide. Les
   ownership-checks reposent **uniquement** sur le filtrage SQL par
   `auth.client_id` côté queries. Compliance V2 ne pourra pas se reposer
   sur `is_admin` pour distinguer humain BO vs customer — il faudra une
   nouvelle règle de classification (cf. § 6).

3. **Deux tables `users` distinctes coexistent et NE DOIVENT JAMAIS être
   confondues :**
   - `users` (1 ligne en local, modèle Prisma Next.js, `id: text/cuid`) =
     **comptes du CMS / BO Next.js uniquement**.
   - `admin_users` (2 lignes en local, modèle Python API, `id: int`) =
     **identifiants d'auth de l'app entière**.
   - Le pont entre les deux : `users.admin_user_id → admin_users.id`.

4. **Les tables `auth_*` (risk score, security decisions, ML features)
   utilisent `user_id INT` qui réfère à `admin_users.id`** — pas à
   `users.id`, pas à `pe_clients.id`. Pour aller du monde métier
   (`client_id` UUID) au monde sécurité (`user_id` INT), il faut traverser
   3 tables : `pe_clients → persons → admin_users`. Aucune jointure
   directe.

5. **Des orphelins existent dans `auth_*`** : exemple constaté en local —
   `auth_global_risk_score.user_id = 1839` n'a aucune ligne correspondante
   dans `admin_users`. La cohérence référentielle entre les tables
   `auth_*` et `admin_users` n'est pas absolue. **Tout tool Compliance V2
   doit gérer ce cas (treat-as-unknown, jamais 500).**

---

## 1. Cartographie des entités d'identité

```
┌──────────────────────────────────────────────────────────────────┐
│  MONDE NEXT.JS / CMS (Prisma)                                    │
│                                                                  │
│  ┌──────────────────┐                                            │
│  │ users            │ id: cuid (text)                            │
│  │ (table Prisma)   │ role: ADMIN | SUPER_ADMIN                  │
│  │  1 ligne         │ admin_user_id: int? ← FK admin_users.id    │
│  └────────┬─────────┘                                            │
│           │                                                       │
└───────────┼───────────────────────────────────────────────────────┘
            │
            │ FK admin_user_id
            ▼
┌──────────────────────────────────────────────────────────────────┐
│  MONDE PYTHON API (SQLAlchemy)                                   │
│                                                                  │
│  ┌──────────────────┐         ┌──────────────────┐               │
│  │ admin_users      │         │ persons          │               │
│  │  id: int (auto)  │         │  id: uuid        │               │
│  │  email           │◀────────│  client_id: uuid? (lien inversé) │
│  │  zero_trust_role │ FK      │  kyc_status      │               │
│  │  person_id?: uuid│────────▶│  account_state   │               │
│  │  ----            │         │  login_frozen    │               │
│  │  2 lignes en loc │         │  profile_json    │               │
│  └────────┬─────────┘         │  57 lignes en loc│               │
│           │                   └────────┬─────────┘               │
│           │                            │                          │
│           │                            │ FK person_id             │
│           │                            ▼                          │
│           │                   ┌──────────────────┐               │
│           │                   │ pe_clients       │               │
│           │                   │  id: uuid        │               │
│           │                   │  status          │               │
│           │                   │  kyc_status      │               │
│           │                   │  email?          │               │
│           │                   │  5 lignes en loc │               │
│           │                   └────────┬─────────┘               │
│           │                            │                          │
│           │ user_id (int)              │ client_id (uuid)         │
│           ▼                            ▼                          │
│  ┌──────────────────────┐    ┌──────────────────────┐            │
│  │ auth_global_risk_    │    │ pe_orders            │            │
│  │ score                │    │ pe_ledger_entries    │            │
│  │ auth_user_risk_*     │    │ pe_portfolios        │            │
│  │ auth_security_*      │    │ pe_product_subscr.   │            │
│  │ auth_session_*       │    │ pe_trades            │            │
│  │ auth_*** (~20 tables)│    │ pe_*** (~25 tables)  │            │
│  └──────────────────────┘    └──────────────────────┘            │
│  (monde "sécurité")          (monde "métier financier")          │
└──────────────────────────────────────────────────────────────────┘
```

### 1.1 Règle d'or pour Compliance V2

**Le `pe_clients.id` (UUID) est le pivot stable et obligatoire** pour tout
raisonnement métier de l'agent. Toute donnée AML/sécurité doit être lue
via le **chemin canonique** :

```
pe_clients.id
   ├─→ pe_clients.person_id  → persons.id
   │                           ├─→ documents.person_id (KYC docs)
   │                           ├─→ registration_sessions.person_id
   │                           └─→ admin_users.person_id
   │                                    └─→ admin_users.id (= "user_id")
   │                                            └─→ auth_global_risk_score
   │                                            └─→ auth_user_risk_*
   │                                            └─→ auth_security_*
   └─→ pe_orders.client_id, pe_ledger_*, pe_*…  (monde métier)
```

L'agent **ne doit jamais** raisonner depuis `auth.user_id` directement —
il doit toujours partir de `auth.client_id` puis suivre les FK.

---

## 2. Cycle de vie d'une identité

| Étape | `persons` | `admin_users` | `pe_clients` | Connexion possible ? |
|---|---|---|---|---|
| **Prospect anonyme** | — | — | — | ❌ |
| **Début registration** (formulaire entamé) | ✅ créé | — | — | ❌ pas encore de credentials |
| **Credentials créés** (mot de passe / OTP / passkey) | ✅ | ✅ créé, `person_id` lié | — | ✅ (mais flow incomplet) |
| **KYC soumis** | `kyc_status='pending'` | ✅ | — | ✅ |
| **Activation client réussie** | `kyc_status='validated'` | ✅ | ✅ créé, `person_id` lié | ✅ |
| **Admin pur (BO Vancelian)** | optionnel | ✅, `person_id=NULL` | — | ✅ (rôle admin) |

→ **Détection automatique du type d'utilisateur (à coder pour Compliance V2)** :

```python
def classify_actor(auth: AuthContext, db: Session) -> ActorKind:
    if auth.client_id is not None:
        return ActorKind.CUSTOMER             # un client métier
    if auth.person_id is not None:
        return ActorKind.ONBOARDING           # registration en cours
    # admin_users.person_id IS NULL → admin BO pur
    return ActorKind.ADMIN_BO
```

Cette fonction n'existe pas encore. **Elle doit être créée en Phase 2a**
comme primitive de la couche tool de l'agent compliance.

---

## 3. Comment l'auth résout aujourd'hui (3 niveaux)

`services/arquantix/api/services/auth/auth_resolution.py`

| Niveau | Fonction | Coût | `client_id` peuplé ? | Quand utilisé |
|---|---|---|---|---|
| **L1 jwt_only** | `resolve_auth_context_jwt_only` | 0 DB query | ❌ toujours `None` | Cache miss + `person_id` dans le JWT |
| **L2 cache** | bundle Redis `auth:user:{id}` | 1 Redis call | ✅ si déjà calculé | Cache hit |
| **L3 db** | `resolve_auth_context_strict_db` | N DB queries | ✅ via `get_client_id_for_person_cached` | Routes financières / sécurité |

**Routes assistance (chat / agents)** utilisent par défaut `get_current_user_or_admin`
= alias de `get_current_user_fast` = niveau L1 prioritaire. **D'où le bug
historique `client_required`** quand le cache rate (cf. § 4).

---

## 4. Le bug `client_required` — explication & fix actuel

### 4.1 Cause racine

```
1. Client mobile envoie POST /assistance/conversations avec Bearer JWT
2. get_current_user_fast() :
     - Décode JWT → admin_user_id, person_id
     - Tente cache Redis → MISS
     - JWT contient person_id → retourne tôt, mode jwt_only
     - AuthContext.client_id = None ❌
3. _require_client(auth) :
     - auth.client_id is None → 403 client_required
```

### 4.2 Fix actuel (`services/assistance/routes.py:104-159`)

Lookup DB ciblé `pe_clients.id WHERE person_id = ?` quand `auth.client_id`
est None mais `auth.person_id` est connu. Patch en place de
`auth.client_id` (Pydantic v2 mutable). **Pas de warm cache global** pour
rester scoped au seul endpoint qui en a besoin.

### 4.3 Limitation persistante

Le fix est **endpoint-local**. Dès qu'un nouvel endpoint Compliance V2
appellera la même résolution sans `_require_client`, il retombera dans
le bug. **Recommandation** : une fois Phase 2a stable, remonter ce fix au
niveau de la dépendance commune `get_current_user_or_admin` (avec un opt-in
via paramètre pour ne pas pénaliser les endpoints qui n'ont pas besoin du
`client_id`).

---

## 5. Gotchas observés en local

### 5.1 `AuthContext.role` toujours `"admin"`

Voir `services/auth/dependencies.py:97`,`186` — hardcodé.
Le `is_admin` property retourne donc toujours `True`. Toute logique de
type *« si admin → bypass ownership check »* (`require_person_access:199`,
`require_client_access_identity:214`) **est court-circuitée** par tout
JWT valide.

→ **Risque** : si un endpoint futur s'appuie sur `auth.is_admin` sans
filtrer par `client_id` en SQL, il y a fuite de données entre comptes.
Toutes les routes assistance actuelles s'en sortent parce qu'elles
filtrent **toujours** par `WHERE client_id = auth.client_id` en SQL.

### 5.2 Orphelins `auth_*`

Constaté en local :
```
auth_global_risk_score.user_id = 1839 (orphelin, pas dans admin_users)
admin_users.id = 1, 2 (les seules vraies entrées)
```

Le `1839` orphelin est probablement un résidu de test ou de migration.
**Tout tool Compliance V2 doit gérer le cas `LEFT JOIN auth_*` →
`NULL`** sans crasher (treat-as-unknown / level=LOW).

### 5.3 `persons` orphelines

57 `persons` en DB, **1 seule** liée à `admin_users`. Les 56 autres sont
soit :
- des `persons` créées au début de registration sans credentials terminés,
- des fixtures de test / dataset hérité.

L'agent compliance ne doit **pas** se préoccuper d'elles directement —
il agit via `pe_clients.id` (5 entrées seulement, toutes propres, toutes
liées à une `persons`).

### 5.4 `email` nullable + index unique partiel

`pe_clients.email` et `admin_users.email` sont `String?` avec un index
unique **partiel** (`WHERE email IS NOT NULL`). Pas un piège pour
Compliance V2 (qui n'a pas à requêter par email), mais à savoir si on
écrit du SQL custom.

### 5.5 Warning Next.js `admin_users.id=1838 FATAL`

Mentionné dans transcription historique. Sans doute en lien avec
l'orphelin 1839 ci-dessus. Ne semble pas bloquant. **À investiguer plus
tard** (audit séparé), pas dans le scope Compliance V2.

---

## 6. Règles non-négociables pour Compliance V2

### Règle 1 — **`client_id` est le pivot, `user_id` est dérivé**

Tout repository / tool de l'agent compliance signe ses fonctions sur
`client_id: str` (UUID stringifié), **jamais** `user_id`. Si un repo a
besoin du `user_id` (pour lire `auth_*`), il fait la traversée
canonique `client_id → person_id → admin_user_id` en interne.

### Règle 2 — **`classify_actor()` avant toute action**

Tout endpoint Compliance V2 commence par classer l'acteur (CUSTOMER /
ONBOARDING / ADMIN_BO). Selon le type :
- **CUSTOMER** → l'agent répond au client lui-même (mode normal).
- **ONBOARDING** → l'agent répond mais avec un mode spécial *« je t'aide
  à finir ta registration »* (cf. axe 1 de Compliance).
- **ADMIN_BO** → **403** : un admin n'a pas à utiliser le chat assistance
  d'un client. (Si un admin veut consulter les chats, c'est via une
  route admin distincte, hors scope agents.)

### Règle 3 — **Tipping-off : ne jamais charger `auth_global_risk_score`
sans filtre serveur**

Le score AML brut est **classifié sensible**. Les tools doivent retourner
un signal **gated** (`safe_to_show: bool`, `client_action: "request_doc"|"escalate"|None`),
**jamais** la valeur brute du score ni du `level`. Le LLM ne reçoit pas
ces champs. Garde matérielle (cf. principe 6 de la spec runtime).

### Règle 4 — **Tolérer les orphelins `auth_*`**

Tout `LEFT JOIN auth_*` → `NULL` se traduit par un signal neutre
(`{"signal": "unknown_risk", "level": null}`), **jamais** une exception.
L'agent doit savoir répondre quand on n'a pas de données auth, sans
panique ni leak d'erreur technique au client.

### Règle 5 — **Distinguo `users` (Prisma) vs `admin_users` (Python)**

Compliance V2 vit **uniquement** côté Python API. Aucun import / jointure
ne doit jamais référencer la table `users` (Next.js CMS). Si on a besoin
du compte CMS d'un admin (cas très théorique), c'est via `users.admin_user_id`
qu'on remonte, jamais l'inverse.

---

## 7. Décisions actées (validées par l'utilisateur le 2026-05-02)

| # | Décision | Statut | Implication |
|---|---|---|---|
| **1** | `ADMIN_BO → 403` sur le chat assistance d'un client. Routes admin distinctes à créer plus tard si besoin de visu admin sur les chats. | ✅ ACTÉ | À implémenter en **Phase 2a** dans `_require_client` (ou son successeur) |
| **2** | Dette technique « `AuthContext.role` hardcodé `"admin"` partout » → backlog **Phase 3+**, pas bloquant Phase 2a. | ✅ ACTÉ | À documenter dans `MULTI_AGENTS_RUNTIME.md` § risques connus |
| **3** | Orphelin `auth_global_risk_score.user_id=1839` → **audit séparé** hors Compliance V2. | ✅ ACTÉ | Ticket à créer (hors scope) |
| **4** | Promouvoir le fix `_require_client` au niveau global (`get_current_user_or_admin`) → en **Phase 2a fin de chantier**, avec opt-in via paramètre. | ✅ ACTÉ | Ne pas perturber le scope d'attaque de Phase 2a, fix en clôture |
| **5** | `classify_actor()` → **4 valeurs** : `CUSTOMER`, `ONBOARDING`, `ADMIN_BO`, **`SUSPENDED`** (quand `persons.login_frozen=true` OU `account_state ∈ ('PARTIAL','BLOCKED')`). | ✅ ACTÉ | À implémenter comme primitive Phase 2a, signature `classify_actor(auth, db) -> ActorKind` |

### 7.1 Conséquence sur la spec runtime

`classify_actor()` devient une **primitive obligatoire** appelée en
amont de tout tool Compliance. Sa signature de référence :

```python
class ActorKind(str, Enum):
    CUSTOMER    = "customer"     # pe_clients existe + pas suspendu
    ONBOARDING  = "onboarding"   # persons existe + pas de pe_clients
    ADMIN_BO    = "admin_bo"     # admin_users.person_id IS NULL
    SUSPENDED   = "suspended"    # login_frozen=true OR account_state IN ('PARTIAL','BLOCKED')

def classify_actor(auth: AuthContext, db: Session) -> ActorKind:
    # 1. Suspended a priorité absolue (gel de sécurité)
    if auth.person_id is not None:
        person = db.query(Persons).filter_by(id=auth.person_id).one_or_none()
        if person is not None:
            if person.login_frozen or person.account_state in ("PARTIAL", "BLOCKED"):
                return ActorKind.SUSPENDED
    # 2. Customer normal
    if auth.client_id is not None:
        return ActorKind.CUSTOMER
    # 3. Onboarding (person sans pe_client)
    if auth.person_id is not None:
        return ActorKind.ONBOARDING
    # 4. Admin BO pur
    return ActorKind.ADMIN_BO
```

**Comportement attendu de l'agent par actor :**

| ActorKind | Chat assistance autorisé ? | Mode agent compliance |
|---|---|---|
| `CUSTOMER` | ✅ | Mode normal (axes 1-3) |
| `ONBOARDING` | ✅ | Mode dédié *« je t'aide à finir ton inscription »* |
| `ADMIN_BO` | **❌ 403** | Code erreur `actor_admin_bo_not_allowed` |
| `SUSPENDED` | ✅ mais **réponse standardisée** | « Ton compte est temporairement gelé. Pour toute question, contacte le support. » Pas de tools, pas de raisonnement métier, pas de leak. |

**SUSPENDED est traité au plus haut niveau** dans le service assistance,
**avant même** d'invoquer le router multi-agent — pour garantir qu'aucun
tool ne s'exécute sur un compte gelé.

---

## 8. Conclusion : zones d'ombre élucidées

| Avant l'audit | Après l'audit |
|---|---|
| « Pas sûr du modèle user_id / client_id » | Cartographie complète § 1, règle d'or `client_id` pivot |
| « Risque de confondre admin et customer » | Distinction = présence `pe_clients` lié, **pas** `is_admin` (cassé) |
| « Pas sûr du robustness » | 5 gotchas listés § 5, dont 2 dettes techniques à inscrire au backlog |
| « Tables `auth_*` reliées à quoi ? » | `user_id INT = admin_users.id`, traversée 3 tables depuis `client_id` |
| « Le bug `client_required` est-il résolu durablement ? » | Fix endpoint-local seulement, à promouvoir global en Phase 2a |

→ **Compliance V2 peut démarrer sans risque** sous réserve d'appliquer
les 5 règles non-négociables du § 6.

→ Le travail **n'a rien cassé** (audit only respecté).

→ Prochain livrable de l'Option X : **`MULTI_AGENTS_RUNTIME.md`** (spec
runtime agentique : function calling itératif, tools introspectifs,
table `agent_decisions`, autonomy levels).
