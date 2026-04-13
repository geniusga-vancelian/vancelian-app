# Audit post-unification DB — Arquantix (web Prisma + API Alembic)

## Executive Summary

Après fusion sur un **seul cluster PostgreSQL**, les régressions observées côté Flutter / Next (`prisma.investmentCategory.findMany()` invalide, `VaultsApiException(500)`) provenaient surtout de :

1. **Migrations Prisma CMS jamais déployées** sur la base unifiée (historique `_prisma_migrations` absent → **P3005** sur `migrate deploy`, tables CMS manquantes).
2. **Conflit de nom de contrainte** : la table API renommée `legacy_json_pages` conservait encore la contrainte/index **`pages_pkey`**, empêchant la création de la table CMS **`pages`** par Prisma (`relation "pages_pkey" already exists`).
3. **`schema.prisma` désaligné** : introspection « db pull » brute ou schéma minimal Git ne correspondaient ni aux migrations ni aux délégués Prisma attendus par le code (`page`, `investmentCategory`, relations `i18n`, `contents`, etc.).

Les correctifs livrés dans le dépôt : migration Alembic **107** (renommage idempotent des contraintes/index/FK `legacy_json_pages`), procédure de **baseline** Prisma documentée ci-dessous, schéma Prisma **reformaté + post-traité** pour coller au code, migration enum **`DOCUMENT`** pour `ArticleBlockType`, endpoint **`GET /api/health/products`**, script **`scripts/singularize_prisma_cms_models.py`** pour rejouer une partie du renommage après un futur `db pull`.

## Broken Modules

| Module | Endpoint Flutter / app | Backend | ORM | Tables (principales) | DB |
|--------|-------------------------|---------|-----|----------------------|-----|
| Exclusive Offers | Contenu souvent via widgets DS / articles / projets CMS + données métier API | Next (routes admin + widgets), API FastAPI pour ordres / portefeuille | Prisma (CMS) + SQLAlchemy (API) | `articles`, `projects`, `ds_components`, côté API `pe_*`, `lending_*`, etc. | `DATABASE_URL` du **web** et de l’**API** doivent être **identiques** en prod unifiée |
| Euro Account / Vaults | `GET /api/mobile/flutter/vaults`, `.../marketing-cards-feed`, landing pages | Next | Prisma | `pages`, `sections`, `section_contents`, `media` | Même `DATABASE_URL` que Prisma |
| Bundles | Listes / config selon surface (admin web, API métier) | Next + FastAPI | Prisma (`bundles`) + SQLAlchemy | `bundles`, `bundle_allocations` | Même cluster ; ownership API pour données transactionnelles |

## DB Mapping

- **API FastAPI** : `services/arquantix/api/.env` → `DATABASE_URL` (SQLAlchemy + Alembic).
- **Next / Prisma** : `services/arquantix/web/.env` → `DATABASE_URL` (client Prisma).
- **Objectif unifié** : les deux URLs doivent pointer vers **la même instance** (même host/port/dbname). Toute divergence recrée des symptômes « moitié OK ».

Vérification rapide (exemple) :

```bash
# Extraire host/port/db sans afficher le mot de passe
python3 -c "from urllib.parse import urlparse; u=urlparse(open('api/.env').read().split('DATABASE_URL=',1)[1].splitlines()[0].strip('\"')); print(u.hostname, u.port, u.path[1:])"
```

## Prisma Audit

- **Introspection seule** après un `db pull` : modèles en `snake_case` / pluriels (`pages`, `investment_categories`) → client `prisma.pages`, etc. **incompatible** avec le code existant.
- **Correctif** : enchaînement `prisma-case-format` (PascalCase + `@map`) puis script `singularize_prisma_cms_models.py` + ajustements manuels des **noms de relations** (`i18n`, `blocks`, `projects`, `contents`, `chapter`, `coverMedia`, `heroMedia`, etc.).
- **Enums** : alignement `ArticleBlockType` avec l’admin (`DOCUMENT`) via migration SQL dédiée.

## Data Audit

- Après `migrate deploy` Prisma, les tables CMS existent mais peuvent être **vides** (`investment_categories`, pages `vault_builder`, etc.) → la home / catégories / vaults peuvent rester vides sans **seed** idempotent.
- Recommandation : exécuter / compléter `web/prisma/seed.ts` (upserts) après déploiement ; ne pas faire de `TRUNCATE` destructif.

## Root Cause

- **Cause principale** : chaîne Prisma CMS non appliquée + blocage `pages_pkey` sur `legacy_json_pages`.
- **Causes secondaires** : absence de baseline `_prisma_migrations`, schéma Prisma non maintenu en phase avec le code (délégués / relations), données CMS non repeuplées après fusion.

## Fix Applied

1. **Alembic 107** — `107_rename_legacy_json_pages_pk_and_indexes.py` (renommage idempotent `pages_pkey` → `legacy_json_pages_pkey`, index, FK).
2. **Baseline Prisma** (sur base déjà peuplée par l’API) :
   - `npx prisma migrate resolve --applied "20260104135006_init_admin_cms"`
   - `npx prisma migrate resolve --applied "20260104135016_init_admin_cms"`
   - `npx prisma migrate deploy`
3. **Schéma** : `prisma-case-format` + `scripts/singularize_prisma_cms_models.py` + corrections manuelles de relations + `@default(cuid())` / `@updatedAt` où le code fait des `create` sans id.
4. **Enum** : migration `20260402160000_add_article_block_type_document`.
5. **Santé** : `web/src/app/api/health/products/route.ts`.

## Seed Strategy

- Garder des **upserts** par clé métier (`slug`, codes produits).
- Environnements : `prisma db seed` après `migrate deploy` ; rejouable sans doublons.

## Tests Added

- Endpoint **`GET /api/health/products`** (compteurs + `vault_config` ok/ko). Des tests automatisés Jest/Vitest peuvent l’appeler en CI (non ajoutés ici pour limiter la portée).

## Remaining Risks

- **Tables help*** absentes** sur certaines bases si migrations conditionnelles n’ont rien créé — les routes help échoueront tant que les tables n’existent pas.
- **Modèle `Email` CMS** absent si la table `emails` n’existe pas en base — routes `prisma.email` à faire évoluer ou table à créer par migration dédiée.
- **Schéma hybride** (147 modèles API + CMS dans un seul `schema.prisma`) : tout nouveau `db pull` **écrase** les conventions ; il faudra **rejouer** format + script + patchs relationnels, ou scinder (schéma CMS only + views) à moyen terme.
- **`npm` / `prisma-case-format`** : l’outil est utile en one-shot ; documenter la procédure plutôt que de multiplier les introspections non contrôlées.

## Procédure opérateur (nouvel environnement unifié)

1. Appliquer **Alembic** jusqu’à **107** (ou exécuter le SQL de renommage si besoin ponctuel).
2. Si `_prisma_migrations` vide et base non vide : `migrate resolve` sur les migrations déjà reflétées par le schéma, puis `migrate deploy`.
3. `npx prisma generate`
4. Seed données CMS minimales (catégories, vaults, etc.).
5. Contrôler `GET /api/health/products`.
