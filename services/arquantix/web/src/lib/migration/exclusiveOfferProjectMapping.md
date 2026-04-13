# Mapping Projects → Vault Builder + Product Registry (Phase 6)

Ce document est la référence **stable** pour `exclusiveOfferProjectMapping.ts`.

## Source (Prisma)

| Source | Champ / emplacement | Notes |
|--------|----------------------|--------|
| `projects` | `id` | `packaged_products.legacy_project_id` |
| `projects` | `slug` | `pages.slug`, `packaged_products.slug` (unicité globale) |
| `projects` | `status` | `ContentStatus` → `PackagedCommercialStatus` (approx.) |
| `projects` | `coverMediaId`, `heroMediaId` | `headerMediaId` = `heroMediaId ?? coverMediaId` |
| `projects` | `youtubeUrl` | non mappé automatiquement (éviter duplication fragile) |
| `projects` | `investmentCategory` | `vault.config.investmentTypeSlug` si slug existe en base (sinon ignoré) |
| `project_i18n` (locale `fr` prioritaire) | `title` | `TitlePage.content.title`, `page.title` |
| | `shortDescription` | `TitlePage.content.subtitle` |
| | `description` | `SimpleMarkdownContentModule` « À propos » |
| | `competitiveAdvantages` (JSON) | `CompetitiveAdvantagesModule` |
| | `howItWorks` (JSON) | `SimpleMarkdownContentModule` « Comment ça marche » |
| | `keyInformation` (JSON) | `KeyInformationModule` |
| | `faq` (JSON) | `FaqAccordionModule` si `items[]` avec `articleSlug` ; sinon contenu FAQ souvent déjà dans `description` |
| `project_media` | ordre + `mediaId` | **Non migré automatiquement** vers carrousel (signaler dans le rapport) |

## Cible (Vault `vault_builder_v1`)

- `config.modules[]` : ordre logique  
  1. `TitlePage`  
  2. `SimpleMarkdownContentModule` (description)  
  3. `CompetitiveAdvantagesModule` (si données)  
  4. `SimpleMarkdownContentModule` (how it works)  
  5. `KeyInformationModule` (si données)  
  6. `FaqAccordionModule` (si items HC)  
  7. `ContentBasDePageSansModuleBlanc` (légal court, fixe)

## Lending existant

Si `lending_pool_products.project_id = projects.id` :

- `lending_pool_products.packaged_product_id` ← packaged créé  
- `packaged_products.engine_type = LENDING`  
- `packaged_products.engine_reference_id` = `lending_pool_products.id` (UUID string)

Pas de nouvelle création Python : uniquement liaison Prisma (aligné phase 5).

## Garde-fous

- Slug `packaged_products` déjà pris par **autre** `legacy_project_id` → conflit explicite.  
- Page existante avec même slug mais `template !== vault_builder` → conflit.  
- Plusieurs LPP pour un `project_id` → conflit (schéma : unique, mais détecté).
