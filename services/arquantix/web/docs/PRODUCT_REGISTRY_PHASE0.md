# Phase 0 — Points d’intégration (audit rapide)

## Tables existantes

| Table | Rôle |
|-------|------|
| `pages` | Pages CMS (`template`, `slug`, `url_path`) |
| `sections` | Sections par page (`key`, ex. `vault_builder_v1`) |
| `section_contents` | JSON publié par locale/statut (`data`) |
| `portfolio_product_configs` | Config modules bundles (`product_code`, `modules`, médias) |
| `projects` | Anciennes offres exclusives (héros, catégorie, statut) |
| `project_i18n` | Contenu localisé projet |
| `project_media` | Galerie |
| `lending_pool_products` | Produit lending lié optionnellement à `project_id` |

## Routes existantes

| Route | Rôle |
|-------|------|
| `GET /api/mobile/flutter/vaults` | Liste vaults (`template=vault_builder`) |
| `GET /api/mobile/flutter/portfolio-products/[productCode]` | Config bundle PE |
| `GET /api/projects` | Liste projets + enrichissement lending (`projects/lending-data`) |
| `GET/POST /api/lending/products/*` | Moteur lending (FastAPI) |

## Points d’intégration pour le Product Registry

1. **Nouvelle table `packaged_products`** : FK `page_id` → `pages`, métadonnées catalogue, `legacy_project_id` → migration.
2. **`lending_pool_products.packaged_product_id`** : lien optionnel 1:1 vers le registre (sans changer la logique pool).
3. **API catalogue** (`/api/mobile/flutter/catalog/products`) : joint registre + contenu VB + enrichissement moteur (lecture seule).
4. **Flutter** : bascule ultérieure vers `CatalogApi` ; `OffersApi` reste jusqu’à Phase 7–8.
