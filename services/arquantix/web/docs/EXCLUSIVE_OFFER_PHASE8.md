# Phase 8 — Exclusive Offers : audit dépendances & dépréciation

> Architecture globale (phases 0–8) : voir [`PRODUCT_REGISTRY_ARCHITECTURE.md`](./PRODUCT_REGISTRY_ARCHITECTURE.md).

## 8A — Audit (synthèse)

### Consommateurs typiques encore présents

| Zone | Usage | Rôle |
|------|--------|------|
| Flutter `OffersRepository` | `CatalogApi` puis repli `OffersApi` | Liste EO — canonique + transitoire |
| Flutter `ExclusiveOfferDetailScreen` | `CatalogApi` puis repli `getProjects` | Détail / CMS |
| Flutter `BlogApi` / `projectArticlesUrl` | `GET /api/projects/:id/articles` | Actualités projet (id legacy ou packaged selon mapping) |
| Flutter `FavoritesApi` | `entityId` = `OfferProject.id` | Souvent `legacy_project_id` |
| Admin `ProjectSelector`, articles | `projects` | Liaisons contenu non EO |
| Admin Projects CMS | CRUD `projects` | Legacy + édition contenus non migrés |
| `GET /api/projects` (public) | Mobile repli, éventuels autres | **Legacy** listing EO |
| Script `seed-exclusive-offer-project.ts` | Upsert projet | Dev / fixtures |

---

## Tableau décisionnel (demandé phase 8)

| Catégorie | Éléments |
|-----------|----------|
| **Safe to remove now** | Aucun chemin critique supprimé dans cette phase (dépréciation seulement). |
| **Keep temporarily** | Repli Flutter `FALLBACK_LEGACY_PROJECTS_ON_CATALOG_FAILURE` ; `GET /api/projects` ; `OffersApi` ; édition admin Projects existants ; `legacy_project_id` sur `packaged_products` ; `create-from-project` si rollback `ADMIN_ALLOW_LEGACY_PROJECT_BASED_EO`. |
| **Keep long-term legacy** | Table `projects` (articles, historique, liens) ; routes admin lecture tant que contenus non purgés ; `GET /api/projects/[id]/articles` tant que l’app lie des actus au projet. |
| **Needs manual decision** | Date de coupure du repli Flutter ; date d’arrêt de `POST` admin projects (activer `ADMIN_BLOCK_PROJECT_BASED_EO`) ; suppression finale de `GET /api/projects` pour EO si d’autres clients HTTP existent. |

---

## Variables d’environnement (référence)

| Variable | Effet |
|----------|--------|
| `ADMIN_BLOCK_PROJECT_BASED_EO=true` | Bloque `POST /api/admin/projects` et `POST /api/admin/lending/create-from-project` (sauf rollback). |
| `ADMIN_ALLOW_LEGACY_PROJECT_BASED_EO=true` | Annule le blocage (rollback contrôlé). |
| `NEXT_PUBLIC_ADMIN_BLOCK_PROJECT_BASED_EO=true` | Désactive les boutons / bannières admin (aligner avec la politique serveur ; figé au build Next). |
| Flutter `--dart-define=FALLBACK_LEGACY_PROJECTS_ON_CATALOG_FAILURE=…` | `true` (défaut) → en cas d’échec catalogue, repli sur `GET /api/projects` via `OffersApi`. `false` → **pas** de repli (l’erreur catalogue remonte). |

---

## Script verify-all

```bash
cd services/arquantix/web
npm run verify:exclusive-offer-registry
npm run verify:exclusive-offer-registry -- --json > report.json
```

Contrôles : pour chaque `packaged_products` avec `productType = EXCLUSIVE_OFFER` — page liée template `vault_builder` ; si `engine_type = LENDING`, cohérence `engine_reference_id` ↔ `lending_pool_products` et `packaged_product_id`.

Tests unitaires : `npm run test:exclusive-offer-registry` ; garde-fous admin : `npm run test:phase8-admin-guards`.

---

## Phase 8Bis — UX admin Exclusive Offers (Vault Builder)

### OFFICIAL ADMIN ENTRY POINT FOR EXCLUSIVE OFFERS

**URL canonique (liste + création)** : [`/admin/vault-builder/exclusive-offers`](https://arquantix.com/admin/vault-builder/exclusive-offers) (adapter le domaine).

- **Liste** : `GET /api/admin/packaged-products/exclusive-offers` — source **`packaged_products`** avec `product_type = EXCLUSIVE_OFFER`, jointure **`pages`** (template `vault_builder`), enrichissement **lending** optionnel (`lending_pool_products` via relation Prisma).
- **Création « clé en main »** : `POST /api/admin/packaged-products/exclusive-offers` — transaction **page Vault Builder** + **`packaged_products`** (type EO, `commercial_status = DRAFT`, `visibility = PUBLIC` par défaut, slug auto `eo-<timestamp>` si non fourni).
- **Édition** : redirection vers **`/admin/vault-builder?slug=<slug>&eo=1`** — même éditeur qu’avant, avec en-tête et encart **« Exclusive Offer »** (parcours : Product Settings → moteur lending → contenu).

**Différences utiles**

| Zone | Rôle |
|------|------|
| **Vault Builder — Exclusive Offers** | Liste dédiée EO, filtres, CTA création, lien vers l’éditeur avec `eo=1`. |
| **Vault Builder (tous les vaults)** | Tous les vaults `vault_builder` ; EO et non-EO côte à côte dans la colonne latérale. |
| **Projects (legacy CMS)** | Legacy articles / contenus non migrés ; **pas** la source catalogue EO. Bannière d’information + garde-fou création si `NEXT_PUBLIC_ADMIN_BLOCK_PROJECT_BASED_EO`. |
| **Lending — EO pools** (`/admin/exclusive-offers`) | Admin **moteur** pools lending ; complémentaire au workspace EO (contenu + registre). |

**Tests** : `npm run test:exclusive-offer-admin-ux` (filtres Prisma listing, sans DB).

**Non-objectifs 8Bis** (inchangés) : pas de modification du moteur lending métier ; pas de suppression de Projects ; pas de changement Flutter ; pas de seconde source de vérité catalogue.
