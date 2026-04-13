# Customer 360 — Rapport d’implémentation (admin Clients)

## Executive summary

Mise en place d’un **module admin durable** pour lister et consulter les **personnes** ayant **démarré l’inscription avec au moins un signal téléphone**, avec une **fiche Customer 360** modulaire, une **progression d’inscription calculée côté backend**, et des **zones explicitement « future-proof »** (transactions, sécurité avancée, AML documents) en placeholder.

L’implémentation respecte la stack existante : **FastAPI**, **SQLAlchemy**, garde **admin/ops** (`require_admin_or_ops`), **Next.js admin** avec routes BFF `/api/admin/customers/*` et pages sous `/admin/customers`.

---

## Source of truth choisie

| Concept | Source |
|--------|--------|
| Identité principale | Table **`persons`** (`Person`) — `profile_json` avec namespace **`collected`** (inscription), `kyc_status`, liaisons futures |
| Compte produit / portefeuille | **`pe_clients`** (`Client`) via `person_id` (relation 1–1 optionnelle) |
| Parcours d’inscription | **`registration_sessions`** + métadonnées session (`status`, `progress_percent`, etc.) |
| Signal téléphone (OTP) | **`two_factor_challenges`** (canal SMS) en complément des champs collectés |

Les champs affichés (mobile, email, noms, pays) sont lus via **`get_person_collected_value`** (cohérent avec le reste du repo) avec slugs connus (`phone_e164`, `email`, `first_name`, etc.).

---

## Règle d’inclusion dans la liste

Un enregistrement **`Person`** apparaît dans le dashboard si **au moins une** des conditions suivantes est vraie :

1. **Session d’inscription** : existe une ligne **`registration_sessions`** avec `person_id` renseigné.
2. **OTP SMS** : existe un **`two_factor_challenges`** pour cette personne avec `channel` contenant **`sms`** (insensible à la casse).
3. **Profil collecté** : `profile_json.collected` contient une valeur non vide pour au moins un slug téléphone :  
   `phone_e164`, `national_phone_number`, `phone`, `mobile_e164`, `mobile_phone`.

Cette règle est **plus large** que « téléphone uniquement dans collected » : elle capture aussi les parcours où le téléphone est porté par le **flux SMS** avant projection complète.

---

## Modèle de calcul du « registration progress »

**Fichier :** `api/services/customers_admin/registration_progress.py`  
**Fonction :** `compute_registration_progress(db, person, pe_client)`.

### Stade canonique (`RegistrationProgressStage`)

Ordre d’affichage par **priorité métier** (le premier qui s’applique gagne le libellé principal) :

| Valeur | Libellé UI (exemple) |
|--------|----------------------|
| `active_client` | Client actif |
| `pe_client_linked` | Compte portefeuille lié |
| `kyc_approved` | KYC approuvé |
| `kyc_pending` | KYC en cours |
| `registration_completed` | Parcours inscription terminé |
| `registration_active` | Parcours en cours |
| `profile_partial` | Identité partielle |
| `phone_started` | Téléphone renseigné (défaut) |

### Jalons (`completed_steps` / `missing_steps`)

Jalons macro stables et extensibles :

- `phone`, `identity_basics`, `registration_flow`, `kyc`, `pe_client_link`, `account_active`

### Ratio

Score sur **6 unités** (phone, identité, session, bonus complétion session, KYC, lien PE + activation) — **normalisé** entre 0 et 1 (`completion_ratio`).

### Source de vérité affichée

Champ `source_notes` : concaténation courte des états bruts (`kyc_status`, statut session, ids PE) pour **audit / support**.

---

## Endpoints créés (backend)

| Méthode | Chemin | Description |
|--------|--------|---------------|
| `GET` | `/api/admin/customers` | Liste paginée + recherche + tri + filtre pays |
| `GET` | `/api/admin/customers/{person_id}` | Détail Customer 360 |

**Query params liste :**

- `page` (défaut 1), `page_size` (1–100, défaut 25)
- `q` : recherche large (profil JSON texte, email, téléphone, noms dans `collected`)
- `sort` : `created_at`, `-created_at`, `updated_at`, `-updated_at` (défaut `-updated_at`)
- `country` : code pays résidence (uppercase, ex. `FR`)

**Auth :** en-têtes `X-Actor-*` — rôles **admin** ou **ops** (identique aux autres routes admin internes).

---

## Pages frontend créées

| URL | Rôle |
|-----|------|
| `/admin/customers` | Liste : tableau, recherche, filtre pays, tri, pagination |
| `/admin/customers/[personId]` | Fiche Customer 360 par **UUID personne** |

**Routes Next (BFF) :**

- `web/src/app/api/admin/customers/route.ts`
- `web/src/app/api/admin/customers/[personId]/route.ts`

**Navigation :** entrée **« Clients »** dans `AdminSidebar` (icône `UserCircle2`).

---

## Colonnes du tableau (liste)

| Colonne | Contenu |
|---------|---------|
| ID personne | Tronqué + infobulle |
| Mobile | Collecté |
| E-mail | Collecté ou e-mail `pe_clients` |
| Prénom / Nom | Collectés |
| Pays | Résidence |
| Progression | Badge libellé + % complétude |
| Créé / Maj | Horodatage `persons` |
| Action | Lien **Fiche** |

---

## Sections de la fiche client

1. **Identité & profil** — données `Person` + champs collectés principaux  
2. **Parcours d’inscription** — dernière session + listes étapes complétées / manquantes + notes de calcul  
3. **KYC & conformité** — `person.kyc_status` + encart d’extension (documents AML : à brancher)  
4. **Compte portefeuille (PE)** — résumé `pe_clients` si présent  
5. **Transactions & mouvements** — **placeholder** explicite  
6. **Sécurité & sessions** — **placeholder** explicite  
7. **Support & technique** — clés `profile_json`, échantillon de slugs `collected`, **extrait limité** des valeurs (pas de dump illimité)

---

## Déjà alimenté vs placeholder

| Zone | État |
|------|------|
| Liste + filtres + pagination | Alimenté |
| Identité depuis `collected` + `Person` | Alimenté (partiel selon données) |
| Progression | Alimenté (logique centralisée) |
| Dernière session d’inscription | Alimenté si session existe |
| Wallet PE | Alimenté si `pe_clients` lié |
| Transactions agrégées | Placeholder |
| Événements sécurité / sessions | Placeholder |
| Documents KYC / AML détaillés | Placeholder (texte d’orientation) |

---

## Limites actuelles

- **Filtre par stade** (`registration_progress.stage`) : non exposé en query SQL (éviter scans lourds) — peut être ajouté via colonne dérivée / vue matérialisée plus tard.
- **Recherche `q`** : `cast(profile_json AS text)` peut être coûteux sur très gros volumes — acceptable pour une V1 admin.
- **Transactions / historique** : non branchés — structure API prête à accueillir un service dédié.
- **JSON brut** : la fiche affiche un **JSON limité** (`raw_profile_excerpt`, max 25 clés) dans la section support — pas de dump complet par défaut sur tout l’écran.

---

## Recommandations (registration / produit)

1. **Normaliser** les slugs téléphone côté inscription pour fiabiliser l’inclusion.
2. **Persister** un champ dérivé `registration_stage` sur `Person` ou une **vue** SQL si les besoins de filtre par stade deviennent critiques.
3. Brancher **transactions** depuis le moteur exchange / custody quand le modèle admin sera figé.
4. Relier **documents** / **AML** existants (`documents`, modules compliance) dans la section KYC.

---

## Fichiers principaux ajoutés ou modifiés

**Backend**

- `api/services/customers_admin/__init__.py`
- `api/services/customers_admin/router.py`
- `api/services/customers_admin/schemas.py`
- `api/services/customers_admin/service.py`
- `api/services/customers_admin/registration_progress.py`
- `api/tests/test_customers_admin.py`
- `api/main.py` (inclusion du router)

**Frontend**

- `web/src/app/admin/customers/page.tsx`
- `web/src/app/admin/customers/[personId]/page.tsx`
- `web/src/app/api/admin/customers/route.ts`
- `web/src/app/api/admin/customers/[personId]/route.ts`
- `web/src/components/admin/AdminSidebar.tsx`

**Documentation**

- Ce rapport : `services/arquantix/CUSTOMERS_ADMIN_DASHBOARD_IMPLEMENTATION_REPORT.md`
