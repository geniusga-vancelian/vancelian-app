# Rapport — récupération des données Dashboard / Widget Builder (Flutter)

## Symptôme

- Tables métier non vides (`investment_categories`, `investment_types`, `pages`, `articles`, …).
- `ds_component_chapters` et `ds_components` à **0**.
- `GET /api/mobile/flutter/layouts/dashboard` → **404** `{ "error": "Chapter not found" }`.

## Chapitre et layout attendus par la route

| Élément | Valeur |
|--------|--------|
| Chapitre Prisma / table `ds_component_chapters.slug` | `component_ds_flutter` |
| Composant layout dashboard / `ds_components.slug` | `dashboard_layout` |
| Contrainte | unique `(chapterId, slug)` |

Fichier route : `web/src/app/api/mobile/flutter/layouts/dashboard/route.ts`.

Alias Flutter supplémentaires (`web/src/app/api/mobile/flutter/layouts/[slug]/route.ts`) : `offers` → `offers_layout`, `euro-account` → `euro_account_layout`, etc.

## Tables et dépendances

| Table | Rôle |
|-------|------|
| `ds_component_chapters` | Chapitres (DS Flutter, Widget Builder widgets/feeds) |
| `ds_components` | Layouts + schémas JSON + widgets builder |
| Pas de FK vers `pages` / `sections` pour ces routes | Lecture directe Prisma |

Routes concernées (extrait) :

- `GET /api/mobile/flutter/layouts/dashboard` — chapitre + `dashboard_layout`.
- `GET /api/mobile/flutter/layouts/[slug]` — même chapitre, slugs résolus via alias.
- `GET /api/mobile/flutter/widgets/[slug]` — chapitres `widget_builder_widgets` et `widget_builder_feeds`.

## Cause racine (conclusion unique)

**B (principale)** : après migration / merge, le **seed principal** (`web/prisma/seed.ts`) ne remplissait pas les tables builder. Le dépôt contenait déjà un seed dédié (`web/prisma/seed-ds-components.ts`) et des scripts ponctuels sous `web/scripts/`, mais ils n’étaient pas invoqués par `npm run db:seed`.

**C** reste possible si une ancienne base avait ces lignes et qu’elles n’ont pas été réimportées : dans ce cas, réexécuter le seed idempotent ci-dessous aligne la cible sans fusion manuelle.

**D** : le slug attendu n’a pas changé dans le code (`component_ds_flutter` / `dashboard_layout`).

## Correctifs appliqués

1. **`seed-ds-components.ts`** : export de `seedDsComponents(db?: PrismaClient)` (idempotent, `upsert`).
2. **`seed-widget-builder-core.ts`** : seed idempotent des chapitres `widget_builder_widgets` / `widget_builder_feeds`, feeds `saving-vaults` / `crypto-bundles`, widgets `widget-saving-vaults-marketing-paysage` / `crypto-bundles-widget`, et layout **`offers_layout`** sous `component_ds_flutter`.
3. **`seed_dashboard_builder.ts`** : enchaîne `seedDsComponents` puis `seedWidgetBuilderCore`.
4. **`seed.ts`** : appelle les deux à la fin du flux principal (même `PrismaClient` que le reste du seed).
5. **`GET /api/health/products`** : champs enrichis (`ds_component_chapters_count`, `ds_components_count`, `dashboard_layout_ok`, `vault_widgets_ok`, `offers_widgets_ok`, `bundles_widgets_ok`). Implémentation : `web/src/lib/health/dashboard-builder-products.ts`.

## Commandes

```bash
cd web
npm run db:seed
# ou uniquement builder / DS Flutter :
npm run db:seed:dashboard-builder
```

## Tests

- Toujours : `npm run test:dashboard-builder` (logique `offers_layout` + suite d’intégration **skippée** par défaut).
- Intégration DB : `ARQUANTIX_DS_SEED_INTEGRATION=1 npm run test:dashboard-builder` (nécessite `DATABASE_URL`).

## Restauration depuis une ancienne base

Si vous devez **fusionner** plutôt que reseeder : exporter / réimporter au minimum les tables **`ds_component_chapters`** et **`ds_components`** (et respecter les contraintes d’unicité sur `(chapter_id, slug)`). Vérifier ensuite les slugs listés ci-dessus.

## Vérification manuelle rapide

```bash
curl -sS http://localhost:3000/api/health/products | jq .
curl -sS -o /dev/null -w "%{http_code}" http://localhost:3000/api/mobile/flutter/layouts/dashboard
```

Attendu après seed : `dashboard_layout_ok: true`, HTTP **200** sur `layouts/dashboard`.
