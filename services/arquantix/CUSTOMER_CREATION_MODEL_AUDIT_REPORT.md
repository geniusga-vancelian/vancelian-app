# Audit modèle — création de compte mobile & Customer 360

**Date :** 2026-04-07  
**Dernière mise à jour (cleanup final) :** 2026-04-07  
**Périmètre :** signup SMS, OTP, `Person`, identité app (`admin_users`), `pe_clients`, CMS Customer 360, profil mobile.

---

## 1. Cartographie actuelle auth / customer

| Rôle | Table / artefact | Rôle technique |
|------|------------------|----------------|
| Identité métier (KYC, inscription, profil) | `persons` | Source canonique **customer** : `profile_json` (layers `collected` / `computed` / `compliance`). |
| Identifiants de connexion app (OTP SMS, JWT `sub`, passkeys…) | `admin_users` | Ligne **credentials** : `email`, `hashed_password`, `mobile_e164`, `person_id`. Le nom de table est historique (« admin ») ; pour l’app mobile ce n’est **pas** un compte back-office staff. Voir docstring du modèle `AdminUser` dans `api/database.py` et module `api/auth.py`. |
| Portefeuille / produit | `pe_clients` | Client PE lié à `persons.id` ; email technique + état KYC produit. |
| Session | `auth_sessions`, JWT | Device binding, refresh, `sec_inc` / `acct_st`. |

**Flux signup mobile (résumé)**  
`POST /auth/signup/sms/verify` : crée ou réutilise `Person` → crée `AdminUser` avec `mobile_e164` + e-mail placeholder `*@signup.internal` → remplit `profile_json.collected.phone_e164` → `issue_fresh_auth_session` → provisionnement `pe_clients` selon règles session.

**Flux login mobile**  
`POST /auth/login/sms/verify` : résout `AdminUser` par `mobile_e164` → session ; **sans** recréer la personne.

---

## 2. Cause racine du mobile manquant dans le CMS

Deux problèmes distincts pouvaient produire un trou ou une incohérence :

### A) Filtre d’éligibilité Customer 360 trop étroit

`services/customers_admin/service.py` — `_eligible_person_filter` — ne listait une `Person` que si **au moins une** des conditions suivantes était vraie :

- session d’inscription (`registration_sessions`),
- ou challenge 2FA SMS historique (`two_factor_challenges`),
- ou téléphone présent dans `profile_json.collected` (clés `phone_e164`, etc.).

Un utilisateur **uniquement** créé par l’app avec connexion OTP pouvait avoir :

- `admin_users.mobile_e164` renseigné,
- `collected.phone_e164` **vide** (ancien bug, import, ou écriture manquée),
- aucune session d’inscription ni 2FA legacy.

→ La personne était **exclue** du filtre : `GET /api/admin/customers/{person_id}` retournait **404** (« not eligible »), ou la ligne n’apparaissait pas en liste — ce qui ressemble à « le mobile n’existe pas » côté produit.

### B) Divergence auth vs profil customer

Même lorsque la fiche existait, `_extract_identity_fields` lisait d’abord `get_person_collected_value(..., "phone_e164")` puis retombait sur `admin_users.mobile_e164`. Si (A) excluait le client, le problème principal était l’éligibilité ; si la fiche s’affichait mais sans mobile, c’était un cas où les deux sources étaient vides ou mal lues.

**Correction livrée :**

1. **Éligibilité** : ajout d’une branche `Person.id IN (SELECT person_id FROM admin_users WHERE mobile_e164 non vide)` pour inclure tout compte app avec mobile de connexion.
2. **Alignement** : fonction `ensure_person_collected_phone_e164` (`services/customer_identity/profile_phone.py`) appelée au **signup** (déjà le cas, factorisé) et au **login SMS** pour remplir `collected.phone_e164` lorsqu’il est vide (backfill progressif à chaque connexion).

---

## 3. Concepts « legacy » encore présents

| Concept | Statut |
|---------|--------|
| Table `admin_users` | **Conservée** : pivot auth réel (JWT, OTP, passkeys). Renommage DB possible plus tard ; coût élevé. **Sémantique produit** : magasin technique d’identifiants applicatifs (voir `database.AdminUser` et `auth.py`), pas « utilisateur CMS » par défaut. |
| E-mail `*@signup.internal` | Identifiant technique non affiché au customer (filtré côté profil mobile / CMS email métier). |
| `services/test_clients/*`, préfixe `/api/app/*` | Rails **portfolio / wallet** pour l’app ; le nom « test » est trompeur. Évolution : renommer en `mobile_app` / `customer_app` par étapes (routers, tags OpenAPI). |
| Customer 360 | Lit `Person` + agrégats ; ne dépend pas des « test clients » pour lister les vrais clients. |

**Ce qui n’est pas requis pour le flux customer final :** aucune dépendance au client « test » PE pour **créer** un compte ou **afficher** la fiche CMS après les correctifs ci-dessus.

---

## 4. Source de vérité customer (canon)

| Donnée | Source canonique affichage / CRM |
|--------|----------------------------------|
| Téléphone (contact) | `person.profile_json["collected"]["phone_e164"]` (E.164). |
| Téléphone connexion OTP | `admin_users.mobile_e164` — **doit être aligné** avec le même numéro ; `ensure_person_collected_phone_e164` synchronise vers `collected` si vide. |
| E-mail contact métier | `collected.email` (pas l’e-mail placeholder login). **Repli liste/fiche** : `pe_clients.email` si `collected.email` vide (affichage CRM uniquement). |
| Prénom / nom / pays | `collected.*` slugs métier (voir `get_person_collected_value` ; alias `given_name` / `family_name`, `country` / `residence_country`). |
| Juridiction | Colonne `Person.jurisdiction` (pas dans `admin_users`). |
| Statut identité « personne » | `Person.status` (`identity.person_status` dans la fiche). |
| Statut produit portefeuille | `pe_clients.status` (`wallet.client_status`) — distinct de `Person.status`. |
| Progression inscription | `customers_admin.registration_progress` + `registration_derived` côté mobile. |

**Règle :** toute donnée visible « customer » dans le CMS ou « Mon compte » doit provenir de `Person.profile_json` (sauf champs purement PE explicites dans `wallet` de la fiche, et repli email PE documenté).

---

## 5. Fichiers modifiés (livraisons)

| Fichier | Changement |
|---------|------------|
| `api/services/customer_identity/profile_phone.py` | **Nouveau** : `ensure_person_collected_phone_e164`. |
| `api/services/customer_identity/__init__.py` | Export du helper. |
| `api/services/auth/signup_mobile_routes.py` | Utilise le helper (remplace le bloc inline) ; supprime import inutile. |
| `api/services/auth/mobile_otp_login_routes.py` | Après vérif OTP, aligne `collected.phone_e164` si vide. |
| `api/services/customers_admin/service.py` | `_eligible_person_filter` inclut les `person_id` avec `admin_users.mobile_e164` ; doc projection identité ; filtre pays `?country=` aligné sur `residence_country` en plus de `country` / `country_of_residence`. |
| `api/database.py` (`AdminUser`) | Docstring : sémantique « magasin identifiants applicatifs » vs admin produit. |
| `api/auth.py` | En-tête de module : lien avec `admin_users` / confusion à éviter. |
| `sql/backfill_person_collected_phone_e164_from_admin_users.sql` | **Nouveau** : preview + update commenté + vérif post-update (voir §6). |

**Tests ajoutés / étendus :**

- `api/tests/test_customer_identity_phone.py`
- `api/tests/test_customers_admin_mobile_eligibility.py`
- `api/tests/test_customers_admin_identity_projection.py` — email (collected vs PE), jurisdiction, `person_status` vs `client_status`.

---

## 6. Backfill données existantes (lot final)

Les comptes déjà en base avec seulement `admin_users.mobile_e164` :

- **Sans se reconnecter :** exécuter le SQL ci-dessous (après backup), ou batch Python via `ensure_person_collected_phone_e164`.
- **Avec reconnexion :** le login SMS remplit désormais `collected.phone_e164` si vide.

### 6.1 Fichier versionné (sûr à l’exécution)

- Chemin : **`services/arquantix/sql/backfill_person_collected_phone_e164_from_admin_users.sql`**
- Contenu : requêtes **preview** + **vérification** exécutables ; bloc **`UPDATE`** dans un commentaire `/* … */` à décommenter volontairement (évite un `psql -f` destructif par accident).

### 6.2 SQL de backfill final (copie dans le rapport)

**Pré-requis :** sauvegarde DB ; exécuter d’abord les SELECT « preview », puis l’UPDATE dans une transaction.

**Champs contrôlés :** uniquement `profile_json.collected.phone_e164`.  
**Non écrasement :** mise à jour seulement si `collected.phone_e164` est NULL ou vide après `trim`.  
**Cohérence :** jointure `admin_users.person_id = persons.id` et `mobile_e164` non vide.

```sql
-- PREVIEW — nombre de lignes
SELECT COUNT(*) AS rows_to_update
FROM persons p
INNER JOIN admin_users u ON u.person_id = p.id
WHERE u.mobile_e164 IS NOT NULL
  AND trim(u.mobile_e164) <> ''
  AND (
    p.profile_json->'collected'->>'phone_e164' IS NULL
    OR trim(p.profile_json->'collected'->>'phone_e164') = ''
  );

-- PREVIEW — échantillon
SELECT p.id, trim(u.mobile_e164) AS admin_mobile_e164,
       p.profile_json->'collected'->>'phone_e164' AS collected_phone_before
FROM persons p
INNER JOIN admin_users u ON u.person_id = p.id
WHERE u.mobile_e164 IS NOT NULL
  AND trim(u.mobile_e164) <> ''
  AND (
    p.profile_json->'collected'->>'phone_e164' IS NULL
    OR trim(p.profile_json->'collected'->>'phone_e164') = ''
  )
ORDER BY p.updated_at DESC NULLS LAST
LIMIT 50;

-- UPDATE (transaction)
BEGIN;
UPDATE persons p
SET profile_json = jsonb_set(
  COALESCE(p.profile_json, '{}'::jsonb),
  '{collected,phone_e164}',
  to_jsonb(trim(both from u.mobile_e164::text)),
  true
)
FROM admin_users u
WHERE u.person_id = p.id
  AND u.mobile_e164 IS NOT NULL
  AND trim(u.mobile_e164) <> ''
  AND (
    p.profile_json->'collected'->>'phone_e164' IS NULL
    OR trim(p.profile_json->'collected'->>'phone_e164') = ''
  );
COMMIT;

-- VÉRIFICATION — même cohorte : attendu 0 après backfill
SELECT COUNT(*) AS remaining_gap_same_cohort
FROM persons p
INNER JOIN admin_users u ON u.person_id = p.id
WHERE u.mobile_e164 IS NOT NULL
  AND trim(u.mobile_e164) <> ''
  AND (
    p.profile_json->'collected'->>'phone_e164' IS NULL
    OR trim(p.profile_json->'collected'->>'phone_e164') = ''
  );
```

**Optionnel (cohorte « app » uniquement)** — ajouter au `WHERE` de l’`UPDATE` si besoin métier :

```sql
  AND COALESCE(u.mobile_app_allowed, true) = true
  AND u.email ILIKE '%@signup.internal'
```

---

## 7. Sweep projection — champs audités (auth vs customer)

| Champ | Source de vérité affichage | Fallback / repli | Trou connu résolu |
|-------|----------------------------|------------------|-------------------|
| **email** | `collected.email` | `pe_clients.email` sur liste + fiche si collected vide | `admin_users.email` **jamais** utilisé pour l’affichage CRM (placeholder signup) |
| **first_name / last_name** | `collected` (+ `given_name` / `family_name`) | Aucun depuis auth | Pas d’écart auth — dépend uniquement de l’inscription / imports |
| **country_of_residence** | `collected` (+ `country`, `residence_country`) | Aucun depuis auth | Filtre liste `?country=` étendu à `residence_country` (aligné sur `_extract_identity_fields`) |
| **jurisdiction** | Colonne `Person.jurisdiction` | — | Pas de champ dupliqué côté auth |
| **Statut customer** | Deux notions : `Person.status` (identité) vs `pe_clients.status` (produit) | — | Documenté dans `_extract_identity_fields` ; tests sur distinction wallet vs identity |

**Décisions de sémantique :**

- **`admin_users`** = magasin technique des identifiants de connexion (doc `AdminUser`, `auth.py`), pas synonyme de « compte admin produit ».
- **E-mail** métier ≠ e-mail ligne auth ; repli PE explicitement pour l’UX liste/fiche quand le profil collecté n’a pas encore d’email.
- **Mobile** = seul champ auth encore projeté en repli (`mobile_e164`) pour parité avec l’historique sans backfill immédiat.

---

## 8. Validations effectuées (tests)

- `pytest api/tests/test_customers_admin_identity_projection.py` — email collected vs PE, jurisdiction, statuts person vs client PE.
- `pytest api/tests/test_customers_admin_mobile_eligibility.py` — éligibilité + mobile depuis auth.
- `pytest api/tests/test_customer_identity_phone.py` — helper téléphone collecté.

---

## 9. Stratégie cleanup / renommage (prochaines étapes)

1. **Documentation & commentaires** : fait (credentials app, `AdminUser`).  
2. **Renommage code** : `test_clients` → `mobile_bootstrap` ou `app_client` (refactor progressif).  
3. **Schéma DB** : migration `admin_users` → `app_users` ou `identity_credentials` (long terme, coordination mobile + web + CMS).  
4. **CMS** : conserver une seule projection (`customers_admin`) ; éviter une deuxième lecture Prisma divergente pour la même personne sans besoin métier.

---

## 10. Risques résiduels

- **Unicité** : `admin_users.mobile_e164` est unique ; les conflits restent gérés par les routes signup/login existantes.  
- **Données volontairement différentes** : si un jour `collected.phone_e164` et `mobile_e164` doivent diverger (changement de numéro), il faudra une règle métier explicite — aujourd’hui l’objectif est l’**alignement**.  
- **Staff réel** : les comptes back-office peuvent aussi être dans `admin_users` ; le filtre d’éligibilité inclut toute personne avec mobile app — affiner avec `mobile_app_allowed` / rôle si nécessaire pour le périmètre « clients uniquement ».

---

## 11. Synthèse

- Le **mobile manquant** au CMS venait surtout du **filtre d’éligibilité** qui ignorait les comptes « mobile-only » sans slug collecté ni session d’inscription.  
- La **source canonique** affichage reste `profile_json.collected` ; l’**auth** reste sur `admin_users` avec synchronisation explicite (téléphone) et documentation claire sur la sémantique des lignes `admin_users`.  
- Le flux customer **ne repose pas** sur un « test client » pour exister ; la nomenclature `test_clients` reste un sujet de **renommage** pour la lisibilité produit.  
- **Backfill SQL** finalisé (preview / update / vérif), fichier versionné sous `services/arquantix/sql/`, sans écrasement des `phone_e164` déjà présents dans `collected`.
