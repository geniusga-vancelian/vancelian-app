# Product Registry — architecture implémentée et suite

## Livré (Phases 0–6)

### Schéma Prisma

- Modèle **`PackagedProduct`** (`packaged_products`) avec enums :
  - `PackagedProductType`, `PackagedCommercialStatus`, `PackagedVisibility`, `PackagedEngineType`
- Relations :
  - `Page.packagedProduct` (1:1)
  - `Project` ↔ `PackagedProduct` via `legacy_project_id` (migration future)
  - `LendingPoolProducts.packagedProduct` + `packaged_product_id` (nullable, unique)

### Migration SQL

- `prisma/migrations/20260410140000_product_registry_packaged_products/migration.sql`
- **Déploiement** : `npx prisma migrate deploy` (ou `migrate dev` en local), puis `npx prisma generate`.

### API Python (lending)

- `services/arquantix/api/services/lending/offer_models.py` : colonne **`packaged_product_id`** (FK `packaged_products.id`, `ON DELETE SET NULL`).
- **Phase 5** : `create_product` accepte en option **`packaged_product_id`** (exclusif avec `project_id` au niveau création).  
  Nouvelle route **`POST /api/lending/products/create-from-packaged-product`** : même orchestration que `create-from-project` (pool + `lending_pool_products`), puis mise à jour **`packaged_products.engine_type = LENDING`** et **`engine_reference_id = lending_pool_products.id`** (SQL dans `OfferService`, sans changer invest / subscribe / lifecycle).

### API catalogue Next.js

- `GET /api/mobile/flutter/catalog/products`  
  - Query : `type`, `visibility`, `commercialStatus`, `locale`, `include_engine_data`, `limit`  
  - Défaut : `visibility=PUBLIC`, `commercialStatus=PUBLISHED`
- `GET /api/mobile/flutter/catalog/products/{slug}`  
  - Query : `locale`, `include_engine_data`  
  - Retour : `packagedProduct`, `page`, `vault.data` (JSON section), `presentation`, `engine.snapshot` (lending si `engineType=LENDING`)

Helpers : `src/lib/catalog/packagedCatalogHelpers.ts`

### Phase 4 — Admin Vault Builder ↔ Product Registry

- **Chargement** : `GET /api/admin/vaults/[slug]` inclut désormais `packagedProduct` (ou `null`) pour la page sélectionnée.
- **Sauvegarde** : après `PUT` du vault (inchangé), `PUT /api/admin/packaged-products/by-page/[pageId]` applique un upsert idempotent (pas de doublon `pageId`, contrôle d’unicité du `slug` hors cette page).
- **UI** : panneau **Product Settings** (`PackagedProductSettingsPanel`) — métadonnées catalogue (toggle, slug, type, etc.).
- **Désactivation** : suppression du `PackagedProduct` si aucune liaison lending ; sinon **409** avec message explicite.
- **Suppression de page vault** : si un `PackagedProduct` existe sans liaison lending, il est supprimé avant la page ; si liaison lending, **409** (cohérent avec la désactivation).
- **Validation** : `src/lib/admin/packagedProductSchemas.ts` (Zod).
- **Tests** : `src/lib/admin/packagedProductSchemas.test.ts` (`npm run test:packaged-registry`).

### Phase 5 — Moteur Lending ↔ Product Registry (Vault Builder)

**Lien canonique (double écriture cohérente)** :

- `packaged_products.engine_type = LENDING`
- `packaged_products.engine_reference_id` = UUID du **`lending_pool_products.id`**
- `lending_pool_products.packaged_product_id` = `packaged_products.id`  
  Contrainte **1:1** (unique sur `packaged_product_id` côté lending).

**Compatibilité legacy** : `lending_pool_products.project_id` et flux `create-from-project` inchangés ; un produit peut avoir `project_id` (CMS ancien) et/ou `packaged_product_id` selon les règles métier (pas les deux imposés au même titre pour une *nouvelle* création depuis packaged : le service refuse `project_id` + `packaged_product_id` simultanés à la création).

**Routes admin Next.js** (`services/arquantix/web`) :

| Méthode | Route | Rôle |
|--------|--------|------|
| GET | `/api/admin/packaged-products/[id]/engine` | Registre + `lendingPoolProduct` Prisma + snapshot FastAPI `GET /api/lending/products/{id}` |
| POST | `/api/admin/packaged-products/[id]/engine/lending/create` | Proxy vers **`POST /api/lending/products/create-from-packaged-product`** |
| POST | `/api/admin/packaged-products/[id]/engine/lending/link` | Lie un `lending_pool_products` sans `packaged_product_id` (transaction Prisma + enums) |
| DELETE | `/api/admin/packaged-products/[id]/engine/lending` | Délie si statut lending **`draft`** uniquement |
| GET | `/api/admin/lending-pool-products/available` | Recherche produits lending non liés (`q`, `limit`) |

**UI** : `PackagedEngineLendingSection` — type de moteur, création lending, liaison existante, snapshot (APR, raised, target, statut, borrower), lien vers `/admin/custody`, déliaison avec confirmation.

**Validations** : type produit **`EXCLUSIVE_OFFER`** pour création/lien lending ; unicités et conflits documentés en réponses **409 / 422**.

**Tests** : `src/lib/admin/packagedEngineSchemas.test.ts` (inclus dans `npm run test:packaged-registry`). Pas de suite d’intégration DB obligatoire dans ce lot (backend Python + Prisma même base en prod).

### Phase 6 — Migration Projects → Vault Builder + Registry

**Objectif** : basculer les Exclusive Offers historiques (table `projects`) vers la chaîne canonique **Page `vault_builder`** + **`packaged_products`** + lien **`lending_pool_products`** existant, **sans** recréer de pool ni modifier le moteur lending.

**Fichiers** :
- Mapping & doc : `src/lib/migration/exclusiveOfferProjectMapping.ts`, `exclusiveOfferProjectMapping.md`
- Orchestration : `src/lib/migration/exclusiveOfferMigrationRunner.ts`
- CLI : `scripts/migrate-exclusive-offers-to-vault.ts` (`npm run migrate:exclusive-offers`)
- Tests mapping : `src/lib/migration/exclusiveOfferProjectMapping.test.ts` (`npm run test:migration-mapping`)

**Sélection des projets** (`--filter`) :
- `lending-linked` (défaut) : projets avec au moins un `lending_pool_products.project_id` (signal fort EO + lending).
- `has-i18n` : au moins une ligne `project_i18n` (large).
- `all` : tous les `projects` (risqué ; dry-run recommandé).

**Idempotence** :
- Si `packaged_products.legacy_project_id = project.id` existe → **skipped** (`ALREADY_MIGRATED`), pas de réécriture du contenu Vault ; réalignement lending si lien partiellement incohérent.
- Slug packaged déjà pris par un **autre** legacy → **conflict** `SLUG_PACKAGED_TAKEN` (pas de suffixe automatique).
- Page même slug mais template ≠ `vault_builder` → **conflict** `PAGE_SLUG_NON_VAULT`.
- Plusieurs LPP pour un même `project_id` → **conflict** `MULTIPLE_LENDING_PRODUCTS`.
- Page vault cible déjà liée à un autre packaged → **conflict** `PAGE_ALREADY_HAS_PACKAGED`.

**Lending** : si un LPP existe pour le projet, mise à jour Prisma uniquement (`packaged_product_id`, `engine_type`, `engine_reference_id`) — aligné phase 5, pas d’appel Python.

**Non couvert automatiquement** : galerie `project_media` → notée dans le rapport ; carrousel / médias à compléter manuellement si besoin.

**Procédure opératoire** :
1. `npm run migrate:exclusive-offers -- --dry-run` (optionnel `--filter=…`)
2. `npm run migrate:exclusive-offers -- --dry-run --project-id=<cuid>` pilote
3. Même commande **sans** `--dry-run` sur le pilote
4. Vérifier admin Vault Builder, registry, engine lending, `GET` catalogue
5. Migration batch sans `--project-id`
6. Contrôle des entrées `conflict` / `error` dans le JSON stdout

### Phase 7 — Flutter : catalogue unifié (Exclusive Offers)

**Avant** : liste et enrichissement CMS via `OffersApi` → `GET /api/projects` (`Config.projectsUrl`).

**Après** (par défaut) : `OffersRepository` appelle `CatalogApi` → `GET /api/mobile/flutter/catalog/products` (`type=exclusive_offer`, `include_engine_data`), puis mappe vers `OfferProject` (`CatalogOfferMapper.fromListItem`). Chaque item expose `legacyProjectId` comme `OfferProject.id` lorsqu’il est présent (favoris, articles liés, tags d’aide).

**Détail écran** : si `OfferProject.catalogSlug` est défini, `ExclusiveOfferDetailScreen` charge `GET /api/mobile/flutter/catalog/products/{slug}` et fusionne vault + `engine.snapshot` (`CatalogOfferMapper.mergeWithDetail`) dans un état local — contenu modularisé (markdown, avantages, FAQ HC, etc.) et métriques lending alignées sur le snapshot Python (`supply_apr`, `current_raised`, `target_size`, `progress_pct`, …).

**Feature flags** (`lib/core/config.dart`) :

| Define | Défaut | Effet |
|--------|--------|--------|
| `USE_CATALOG_FOR_EXCLUSIVE_OFFERS` | `true` | `false` → liste uniquement via `GET /api/projects` |
| `FALLBACK_LEGACY_PROJECTS_ON_CATALOG_FAILURE` | `true` | `false` → pas de repli si le catalogue échoue (erreur remontée) |

**Fichiers Flutter** : `lib/features/offers/data/catalog_api.dart`, `domain/models/catalog_product.dart`, `domain/catalog_offer_mapper.dart`, `data/offers_repository.dart`, écran `presentation/screens/exclusive_offer_detail_screen.dart`. Tests : `test/features/offers/catalog_offer_mapper_test.dart`.

**Limites** : galerie médias non portée automatiquement depuis l’ancien CMS (cf. phase 6).

### Phase 8 — Dépréciation Projects / repli Flutter / garde-fous admin

**CANONICAL FLOW** (officiel) : Vault Builder (page `vault_builder`) → `packaged_products` → moteur lending (optionnel) → `GET /api/mobile/flutter/catalog/products` (+ détail par slug) → Flutter `CatalogApi` / `OffersRepository`.

**LEGACY FLOW** (transitoire) : table `projects` + `GET /api/projects` → Flutter `OffersApi` / repli catalogue ; `GET /api/projects/[id]/articles` pour actualités liées ; favoris / tags d’aide sur `project.id` lorsque `legacy_project_id` est renseigné.

**DEPRECATION STATUS** :

| Élément | Statut |
|---------|--------|
| `GET /api/mobile/flutter/catalog/products` | **Canonique** (liste EO) |
| `GET /api/projects` | **Legacy** pour listing EO — en-têtes `Warning` + `X-Arquantix-Deprecated-Use-Instead` ; pas de suppression dans cette phase |
| `OffersApi.getProjects` | **Legacy** — repli Flutter ; commentaires dartdoc |
| `POST /api/admin/projects` | Peut être **bloqué** par `ADMIN_BLOCK_PROJECT_BASED_EO=true` (rollback : `ADMIN_ALLOW_LEGACY_PROJECT_BASED_EO=true`) |
| Proxy `POST /api/admin/lending/create-from-project` | Même garde-fou |
| Script `npm run verify:exclusive-offer-registry` | **Vérification** cohérence Prisma (page vault, lending ↔ packaged) |

**NEXT SAFE REMOVALS** (non effectués ici) : retirer le repli Flutter (`FALLBACK_LEGACY_PROJECTS_ON_CATALOG_FAILURE=false` puis suppression du code de fallback) ; arrêter `GET /api/projects` pour EO quand aucun consommateur externe ; retirer `OffersApi.getProjects` si plus d’appel.

**Procédure avant coupure repli Flutter** : basculer staging sur `FALLBACK_LEGACY_PROJECTS_ON_CATALOG_FAILURE=false` ; surveiller erreurs ; exécuter `npm run verify:exclusive-offer-registry -- --json` en CI ou post-déploiement.

**Procédure avant suppression `GET /api/projects` pour EO** : inventaire des clients (mobile, web, scripts) ; migration des usages restants ; conserver l’endpoint si d’autres produits/pages dépendent encore de `projects`.

Voir aussi : `docs/EXCLUSIVE_OFFER_PHASE8.md` (audit dépendances, tableau safe / keep / legacy).

## Non implémenté (phases suivantes — à planifier)

| Phase | Contenu |
|-------|---------|
| 9+ | Suppression code mort après période de stabilité ; éventuel retrait table `projects` **uniquement** si plus aucun usage métier (décision manuelle) |

## Tests de non-régression (manuel / CI)

1. `npx prisma validate` + `npx prisma migrate deploy` sur une copie de base.
2. `npx tsc --noEmit` dans `web/`.
3. Après insertion manuelle d’un `PackagedProduct` + page `vault_builder` : `GET /catalog/products` retourne 200.
4. Côté API : smoke test lecture `LendingPoolProduct` après migration (colonne nullable).

## Rollback

- SQL indicatif en tête du fichier de migration Prisma.
- Retirer la colonne `packaged_product_id` côté SQLAlchemy si rollback code + DB.
