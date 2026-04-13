# Product Platform — Phase 9 (design & architecture uniquement)

> **Statut** : document de cadrage — **aucune implémentation métier** validée par ce fichier seul.  
> **Références internes** : [`services/arquantix/web/docs/PRODUCT_REGISTRY_ARCHITECTURE.md`](../services/arquantix/web/docs/PRODUCT_REGISTRY_ARCHITECTURE.md), [`services/arquantix/web/docs/EXCLUSIVE_OFFER_PHASE8.md`](../services/arquantix/web/docs/EXCLUSIVE_OFFER_PHASE8.md).

---

## 1. Executive summary

La plateforme a déjà validé sur les **Exclusive Offers** une chaîne cible : **Vault Builder (contenu)** → **`packaged_products` (registre catalogue)** → **moteur métier (ex. lending)** → **`/api/mobile/flutter/catalog/*` (contrat lecture client)** → **Flutter / web**.

La **Phase 9** doit **généraliser ce pattern** à tous les produits packagés **sans** multiplier les sources catalogue, les flux admin par famille, ni les endpoints publics hétérogènes.

**Règle d’or à figer** : *tout produit packagé visible dans l’app doit exister comme une ligne `packaged_products`*, avec un **type**, une **visibilité**, un **statut commercial**, et des **liens** explicites vers page Vault et moteur.

Ce document fournit : audit **ancré sur le repo**, principes, **trois contrats** (catalogue, moteur, rendu), **matrice de capacités**, plan d’absorption du legacy, roadmap 9A–9E, risques et anti-patterns.

---

## 2. Audit du code existant (base factuelle)

### A. Product Registry

| Élément | Emplacement / détail |
|--------|----------------------|
| Modèle | `PackagedProduct` dans `services/arquantix/web/prisma/schema.prisma` — champs : `id`, `slug`, `pageId`, `productType`, `commercialStatus`, `visibility`, `featuredRank`, `categorySlug`, `tags`, `engineType`, `engineReferenceId`, `legacyProjectId`, `createdAt`, `updatedAt`, `publishedAt` |
| Enums | `PackagedProductType` : `VAULT_SIMPLE`, `EXCLUSIVE_OFFER`, `MANAGED_MANDATE`, `CRYPTO_BUNDLE` — `PackagedCommercialStatus`, `PackagedVisibility`, `PackagedEngineType` |
| Relations | `Page` 1:1 `packagedProduct` ; `LendingPoolProducts` optionnel 1:1 via `packaged_product_id` ; `legacyProjectId` → `Project` |
| Admin | `PUT/GET /api/admin/packaged-products/by-page/[pageId]` ; `PackagedProductSettingsPanel` ; scripts verify registry (`verify-exclusive-offer-registry`, tests Zod) |
| EO dédié (8Bis) | `GET/POST /api/admin/packaged-products/exclusive-offers` — liste / création EO sur registre + page vault |

### B. Vault Builder

| Élément | Détail |
|--------|--------|
| Données | `Page` (`template = vault_builder`), `Section` (`key = vault_builder_v1`), `SectionContent` par locale / statut (DRAFT / PUBLISHED) |
| API admin | `GET/POST /api/admin/vaults`, `GET/PUT/DELETE /api/admin/vaults/[slug]` — charge `packagedProduct` sur GET détail |
| UI | `services/arquantix/web/src/app/admin/vault-builder/page.tsx` — modules, Product Settings, moteur lending (`PackagedEngineLendingSection`), Publier/Dépublier EO sur registre |
| Liste EO | `/admin/vault-builder/exclusive-offers` |

### C. Moteurs / assimilables

| Zone | Rôle actuel (repo) |
|------|-------------------|
| **Lending** | `PackagedEngineType.LENDING`, `engine_reference_id` → `lending_pool_products.id` ; snapshot via `fetchLendingEngineSnapshot` → FastAPI `GET /api/lending/products/{id}` ; admin create/link/unlink sous `/api/admin/packaged-products/[id]/engine/lending/*` |
| **Bundles crypto** | Portfolio Engine : produits / configs (`/api/admin/portfolio-engine/products`, configs par `product_code`), UI dans Vault Builder (section « Produits Portfolio Engine »), **pas** encore un parcours unique `packaged_products` + catalog pour tous les bundles |
| **Vaults simples** | Pages `vault_builder` + éventuel `packaged_products` type `VAULT_SIMPLE` — même mécanique pages/sections que les EO côté CMS |
| **Mandates** | Enum `MANAGED_MANDATE` / `MANAGED_PORTFOLIO` présents ; pas de chaîne admin + catalog complète documentée comme pour EO dans ce repo à date |

### D. API catalogue (Next.js)

| Route | Rôle |
|-------|------|
| `GET /api/mobile/flutter/catalog/products` | Liste `packaged_products` avec filtres `type`, `visibility`, `commercialStatus`, `locale`, `include_engine_data`, `limit` — défauts typiquement `PUBLIC` + `PUBLISHED` |
| `GET /api/mobile/flutter/catalog/products/{slug}` | Détail : métadonnées packaged, `presentation` (titre/sous-titre/cover depuis vault), `vault.data`, `engine.snapshot` si lending + flag |
| Helpers | `services/arquantix/web/src/lib/catalog/packagedCatalogHelpers.ts` |

**Limites actuelles** : enrichissement **snapshot** principalement branché pour **LENDING** dans les routes catalogue listées ; les autres `engine_type` sont représentés dans le schéma mais le pipeline snapshot unifié multi-moteurs reste à compléter en implémentation.

### E. Flutter (et parallèles)

| Composant | Chemin (repo) | Rôle |
|-----------|----------------|------|
| `CatalogApi` | `services/arquantix/mobile/lib/features/offers/data/catalog_api.dart` | `GET .../catalog/products` + détail par slug |
| `CatalogOfferMapper` | `.../offers/domain/catalog_offer_mapper.dart` | Mapping liste + fusion détail EO |
| `OffersRepository` | `.../offers/data/offers_repository.dart` | EO : catalogue canonique ; repli optionnel `OffersApi` → `GET /api/projects` selon `Config` |
| `ProductCatalogApi` | `.../markets/data/product_catalog_api.dart` | Flux **distinct** (`getBundleCatalog`, `getDisplayConfigs`) — **parallèle** au catalogue packaged |
| Écrans | `ExclusiveOfferDetailScreen`, `crypto_bundles_widget.dart`, `bundle_selection_screen.dart`, `product_preview_screen.dart` | Consommateurs directs ou indirects |
| `Config` | `lib/core/config.dart` | `catalogProductsUrl`, `projectsUrl`, flags `USE_CATALOG_FOR_EXCLUSIVE_OFFERS`, `FALLBACK_LEGACY_PROJECTS_ON_CATALOG_FAILURE` |

### F. Web public / legacy

- `GET /api/projects` : documenté comme **legacy** pour listing EO (dépréciation Phase 8) ; articles projet, favoris, etc.  
- Garde-fous admin `projectExclusiveOfferGuards`, bannières Projects, migration CLI EO → vault.

---

## 3. Principes d’architecture (à figer)

1. **Visibilité app** ⇒ **exactement une ligne** `packaged_products` (identité + liens + statut catalogue).
2. **Vault Builder** = contenu éditorial riche **uniquement** — pas de statut métier catalogue ni logique moteur dans le JSON vault.
3. **Product Registry** = **seule source de vérité** pour typage catalogue, visibilité, ranking, slug catalogue, lien `page_id` / moteur.
4. **Moteurs** = services spécialisés (lending, bundle, mandate, vault metrics, …) — **pas** de logique métier copiée dans le catalogue.
5. **Catalog API** = **orchestrateur** : résout `engine_type` + `engine_reference_id`, appelle **resolvers** par type, assemble présentation + snapshot **sans** connaître les détails internes de chaque moteur.
6. **Legacy** (`projects`, configs bundle isolées, etc.) peut vivre comme **historique**, **pont**, ou **données moteur** — **pas** comme deuxième source catalogue pour le même produit exposé aux clients.
7. **Admin** = **générique** (Content / Catalog / Engine / Distribution) + **capability matrix** par `product_type` — pas d’écran divergent par famille hors matrice.

**Anti-positionnement explicite** : pas de « tout mettre dans Vault Builder » au sens métadonnées catalogue ; pas de nouveau catalogue parallèle sans plan de dépréciation ; pas de `legacy_project_id` comme clé fonctionnelle long terme.

---

## 4. Contrat catalogue (registry)

### 4.1 Champs (`packaged_products`) — proposition stable

| Champ | Rôle | Source de vérité |
|-------|------|------------------|
| `id` | UUID registry | DB |
| `slug` | Identifiant catalogue stable (URL app) | Registry ; unique global |
| `product_type` | Famille produit | Registry enum |
| `commercial_status` | DRAFT / PUBLISHED / ARCHIVED | Registry |
| `visibility` | PUBLIC / PRIVATE / HIDDEN | Registry |
| `featured_rank` | Tri / mise en avant | Registry |
| `category_slug` | Taxonomie / filtres | Registry |
| `tags` | JSON tags | Registry |
| `page_id` | Lien 1:1 vers page Vault Builder | Registry |
| `engine_type` | Type moteur (nullable si sans moteur) | Registry |
| `engine_reference_id` | ID dans le domaine moteur (string) | Registry |
| `published_at` | Date publication métier catalogue | Registry (dérivée / mise à jour selon règles) |
| `legacy_project_id` | Pont historique CMS | Registry ; **transitoire** |

**Agrégé côté BFF** (pas stocké en DB registry) : titre/sous-titre/cover « présentation » issus du vault (`resolveVaultPresentation`), plus `engine.snapshot` selon résolveur.

### 4.2 Répartition stricte

| Donnée | Registry | Vault JSON | Moteur |
|--------|----------|------------|--------|
| Slug catalogue | ✓ | ✗ | ✗ |
| Type / statut commercial / visibilité | ✓ | ✗ | ✗ |
| featured_rank, category, tags | ✓ | ✗ | ✗ |
| engine_type + reference | ✓ | ✗ | ✓ (données autoritaires côté moteur) |
| Textes marketing, modules, médias | ✗ | ✓ | ✗ |
| APR, raised, allocation live | ✗ | ✗ | ✓ (exposé via snapshot) |

### 4.3 « Do not put these fields in Vault Builder JSON »

Ne **pas** stocker dans `section_contents.data` (config vault) en tant que vérité canonique :

- statut commercial, visibilité catalogue, `featured_rank` « source of truth »
- `engine_type` / IDs moteur / APR / montants investissables
- règles d’éligibilité investisseur, flags réglementaires catalogue
- identifiants `legacy_project_id` comme clé runtime

Ces champs appartiennent au **registry** et/ou au **moteur** ; le vault peut éventuellement **afficher** des libellés dérivés en lecture seule côté UI admin si un jour on duplique pour preview — pas pour persistance métier.

---

## 5. Contrat moteur (snapshot)

### 5.1 Noyau générique (tous moteurs)

Proposition de **socle** dans `engine.snapshot` (noms indicatifs, à valider avec chaque domaine) :

| Champ | Type | Obligatoire | Description |
|-------|------|-------------|-------------|
| `status` | string | oui | État métier (ex. `fundraising`, `closed`) |
| `investable` | bool | recommandé | Souscription possible |
| `risk_level` | string? | non | Niveau risque normalisé |
| `horizon` | string? | non | Horizon / durée |
| `yield_target` ou `performance_target` | number? | non | Selon produit |
| `currency` | string? | non | Devise principale |
| `subscription_min` | number? | non | Ticket min |
| `progress` | number? | non | 0–100 si applicable |

### 5.2 Extensions par moteur (exemples)

| `engine_type` | Extension typique |
|---------------|-------------------|
| `LENDING` | `supply_apr`, `current_raised`, `target_size`, `product_id`, `asset`, `entry_asset_default`, … (aligné snapshot Python actuel) |
| `BUNDLE` | allocations, instruments, frais, rebalance cadence |
| `MANAGED_PORTFOLIO` | stratégie, benchmark, frais, contraintes mandat |
| `VAULT_ENGINE` | métriques yield / liquidité / lock-up |

### 5.3 Résolution

- Le catalogue **ne contient pas** de `switch` métier éparpillé : **un module** `resolveEngineSnapshot(engineType, referenceId)` (ou équivalent) délègue à des **adapters** par type.
- Champs **obligatoires** du socle : à définir par moteur dans la matrice ; champs **optionnels** documentés par version de snapshot.

---

## 6. Contrat de rendu / Vault Builder

### 6.1 Rôle

Vault Builder porte le **contenu produit** : hero, résumés, faits clés, FAQ, bénéfices, process, disclosures, médias, CTA — sous forme de **modules** typés dans le JSON `vault_builder_v1`.

### 6.2 Ce qui ne doit pas y être

Voir §4.3. Le vault n’est **pas** le registre catalogue ni la base transactionnelle moteur.

### 6.3 Layouts non figés par type

- Comportements spécifiques (ex. barre de progression, doc légale) sont pilotés par **`product_type` + capability matrix** côté app admin et clients — pas par un template différent par produit **sans** règle centralisée.

### 6.4 Tableau obligatoire — `product_type` → modules autorisés / recommandés

| product_type | Modules recommandés (Vault) | Modules optionnels | À éviter sans besoin métier |
|--------------|----------------------------|--------------------|----------------------------|
| `vault_simple` | `TitlePage`, `SimpleMarkdownContentModule`, médias | FAQ, key facts | surcharge modules finance |
| `exclusive_offer` | `TitlePage`, `CompetitiveAdvantagesModule`, `KeyInformationModule`, markdown | `FaqAccordionModule`, transactions | métriques lending **dupliquées** dans le vault (source = snapshot) |
| `crypto_bundle` | `TitlePage`, `AllocationModule`, `PerformanceChart` | marketing cards | allocations **source de vérité** dans le vault si le moteur bundle les porte |
| `managed_mandate` | `TitlePage`, markdown conformité, FAQ | steps, key info | paramètres mandat **autoritaires** dans le vault |

*(Affinage par atelier produit / compliance.)*

---

## 7. Capability matrix (centrale)

### 7.1 Tableau 1 — `product_type` → moteur(s) autorisé(s)

| product_type | Moteur(s) autorisés | Notes |
|--------------|---------------------|-------|
| `vault_simple` | `VAULT_ENGINE` ou aucun | Pages info / onboarding |
| `exclusive_offer` | `LENDING` (typique) | Déjà branché |
| `crypto_bundle` | `BUNDLE` | Config PE aujourd’hui hors registry |
| `managed_mandate` | `MANAGED_PORTFOLIO` | À brancher |
| `structured_product` *(futur)* | TBD | Nommer sans sur-détailler |
| `rwa_income` / `rwa_equity` / `lombard_strategy` *(futurs)* | TBD | Idem |

### 7.2 Tableau 2 — `product_type` → modules autorisés / recommandés

*(Voir §6.4 — même contenu ; ce tableau est la référence produit/design.)*

### 7.3 Tableau 3 — `product_type` → zones de distribution

| product_type | App mobile | Web | Autres |
|--------------|------------|-----|--------|
| `exclusive_offer` | Liste Investir (catalog) | landing / deeplink | notifications |
| `crypto_bundle` | Marchés / bundles | widgets | — |
| `vault_simple` | Contenu éducatif | pages publiques | — |
| `managed_mandate` | Parcours conseiller / client | espace dédié | — |

*(À caler sur navigation réelle et conformité.)*

### 7.4 Tableau 4 — `engine_type` → contrat snapshot (socle + extension)

| engine_type | Socle générique | Extension typique |
|-------------|-----------------|-----------------|
| `LENDING` | `status`, `investable`, `progress` | APR, raised, target, asset, lending `product_id` |
| `BUNDLE` | `status`, `investable`, `currency` | allocations, symboles, frais |
| `MANAGED_PORTFOLIO` | `status`, `risk_level`, `horizon` | benchmark, frais, contraintes |
| `VAULT_ENGINE` | `yield_target`, `horizon` | liquidité, lock-up |

---

## 8. Admin générique (cible)

**Onglets cibles** (alignés Phase 9 / 8Bis et au-delà) :

| Onglet | Contenu |
|--------|---------|
| **Content** | Modules vault, médias, hero, sections |
| **Catalog** | `product_type`, slug, visibilité, statut, rank, catégorie, tags |
| **Engine** | `engine_type`, référence, création / lien / unlink, snapshot, lien admin moteur |
| **Distribution** | placements app (sections, featured), év. audience / locale |

**Commun** : tous les `packaged_products` liés à une page `vault_builder`.  
**Spécifique** : champs conditionnels selon **capability matrix** (pas un nouvel écran par famille sans passer par la matrice).

Réutilisation : UX EO (liste dédiée, Publier/Dépublier, Product Settings, lending) comme **modèle** pour les autres types.

---

## 9. Plan d’absorption des systèmes parallèles

### 9.1 `LEGACY SOURCES TO ABSORB`

| Système | Rôle actuel | Cible Phase 9 | Action |
|---------|-------------|---------------|--------|
| **EO + registry** | Canonique | Référence | Maintenir ; étendre pattern |
| **Bundles / `portfolio_product_configs` / PE API** | Catalogue effectif bundles | Moteur + **référence registry** pour toute visibilité app unifiée | Migrer vers `packaged_products` + `engine_type=BUNDLE` + snapshot |
| **Vaults simples** | Pages + éventuellement sans registry | **Ligne packaged** pour toute entrée catalogue | Création / migration contrôlée |
| **`projects` CMS** | Articles, historique, legacy EO | **Pont** `legacy_project_id`, pas source catalogue | Déprécier listing EO ; garder articles |
| **`GET /api/projects` (public)** | Repli Flutter | Déprécier après bascule clients | Headers dépréciation déjà posés côté web (Phase 8) |
| **ProductCatalogApi Flutter (bundles)** | Parallèle catalog | Consommer **catalog unifié** ou adapter temporaire documenté | Éviter double source long terme |

---

## 10. Plan de migration par famille de produit

| Famille | État actuel (indicatif) | Cible | Jalons |
|---------|-------------------------|-------|--------|
| **exclusive_offer** | Chaîne EO + registry + lending + Flutter catalog | **Référence** — ne pas diverger | Maintenir ; étendre seulement via matrix |
| **crypto_bundle** | PE + `ProductCatalogApi` + vault sections portfolio | `packaged_products` (`CRYPTO_BUNDLE`) + `BUNDLE` + snapshot + **un** flux catalogue | 9B |
| **vault_simple** | Pages vault, visibilité catalogue inégale | Ligne registry pour tout SKU listé / filtrable | 9C |
| **managed_mandate** | Enum + peu ou pas de pipeline complet | `MANAGED_MANDATE` + `MANAGED_PORTFOLIO` + mandat engine | 9D |
| **Futurs** (structured, RWA, lombard) | N/A | Nouveaux `product_type` / `engine_type` dans Prisma **après** design matrix | hors périmètre détail Phase 9 |

Ordre recommandé : **EO stable → bundles (plus gros parallèle) → vaults simples → mandates → cleanup endpoints**.

---

## 11. Roadmap recommandée (documentaire)

| Phase | Objectif | Dépendances | Risque | Gain |
|-------|----------|-------------|--------|------|
| **9A** Design canonique | Figurer contrats, matrix, résolveurs | — | sous-estimation périmètre | Cadre unique pour PRs |
| **9B** Bundles | `CRYPTO_BUNDLE` + moteur bundle + catalog | 9A, stabilité PE | régression widgets | une source catalogue bundles |
| **9C** Vaults simples | `VAULT_SIMPLE` partout où besoin listing | 9A | volume pages | cohérence admin + API |
| **9D** Mandates | `MANAGED_MANDATE` + moteur | 9A, dispo métier | compliance | parcours unifié |
| **9E** Cleanup | Retrait routes parallèles, flags, doc | 9B–9D | clients externes | dette réduite |

---

## 12. Risques majeurs

1. **Double écriture** registry vs moteur mal synchronisée → états incohérents visibles dans l’app.  
2. **Snapshot multi-moteurs** : explosion de `if` dans le BFF sans adapters.  
3. **Bundles** : migration depuis PE sans **fenêtre** de coexistence documentée.  
4. **Flutter** : oublis de repli / double fetch catalogue + ancienne API.  
5. **Admin** : pression pour des **écrans spéciaux** hors matrice → dette UX.

---

## 13. ANTI-PATTERNS / DEBTS TO AVOID

1. Remettre du **métier catalogue/moteur** dans le JSON Vault Builder.  
2. Laisser **plusieurs sources catalogue** vivantes pour le même objet utilisateur.  
3. Créer une **UI admin spéciale** par produit **hors** capability matrix.  
4. Faire de **`legacy_project_id`** une fondation durable (rester un **pont**).  
5. Faire **connaître au catalogue** les détails internes de chaque moteur (tout doit passer par snapshot + contrat).  
6. **Multiplier les endpoints catalogue** en doublon **sans** stratégie de dépréciation et date de coupure.

---

## 14. Modules / fichiers probablement impactés (implémentation future — non exhaustif)

*Ne modifie pas ces fichiers par ce seul document ; liste pour planification.*

**Web (Next)**  
`prisma/schema.prisma` · `src/lib/catalog/packagedCatalogHelpers.ts` · `src/app/api/mobile/flutter/catalog/products/route.ts` · `src/app/api/mobile/flutter/catalog/products/[slug]/route.ts` · `src/app/admin/vault-builder/**` · `src/app/api/admin/packaged-products/**` · `src/lib/admin/packagedProductSchemas.ts` · routes `portfolio-engine/**`

**Flutter**  
`lib/features/offers/data/catalog_api.dart` · `offers_repository.dart` · `lib/features/markets/data/product_catalog_api.dart` · `lib/core/config.dart` · écrans consommant bundles vs catalog

**API Python**  
`services/arquantix/api/services/lending/**` · endpoints bundle / mandat selon évolution

**Docs**  
`PRODUCT_REGISTRY_ARCHITECTURE.md` · `EXCLUSIVE_OFFER_PHASE8.md` · ce fichier

---

## 15. Critères de réussite (Phase 9 exécutée plus tard)

- Une **équipe peut ouvrir une PR** « bundle » ou « vault simple » avec référence à **ce doc** + matrix + contrats.  
- Pas de **nouvelle** source catalogue sans ligne `packaged_products` justifiée et plan de migration.  
- **Catalog API** reste le **point d’entrée** lecture pour les clients pour les produits packagés exposés.

---

*Fin du document Phase 9 (architecture / design uniquement).*
