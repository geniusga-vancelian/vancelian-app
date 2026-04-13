# Blog & CMS — récupération post-unification DB

## Root Cause

1. **Client / schéma Prisma désalignés** après introspection ou migrations partielles → erreurs du type **`prisma.investmentCategory.findMany()` invalid invocation** (délégué ou relations absentes du client généré).
2. **Relation blog incorrecte sur les blocs** : le schéma exposait `articleBlockI18n` sur `ArticleBlock` alors que le code (`getArticleBySlug`, includes `blocks: { include: { i18n: … } }`) attendait le champ relation **`i18n`**. Toute requête détail article avec blocs pouvait faire échouer Prisma à la validation.
3. **Données CMS vides** après fusion : tables présentes mais **aucun article `PUBLISHED`** ni parfois **aucune ligne** dans `investment_categories` si le seed n’a pas été rejoué → feed vide (200) ou confusion côté produit (« Lorem ipsum », widgets sans texte métier).

Une réponse **500** sur `GET /api/blog` survient lorsque **Prisma lève** (schéma/client/DB incohérents) ou en cas d’erreur non gérée en aval. **L’absence de contenu** ne provoque pas d’exception Prisma : dans ce cas la route renvoie déjà des listes vides en **200**.

## Prisma Issues

| Problème | Correctif |
|----------|-----------|
| `ArticleBlock` relation vers i18n mal nommée | `articleBlockI18n` → **`i18n`** ; côté `ArticleBlockI18n`, relation inverse **`block`** + `@default(cuid())` / `@updatedAt` sur `updated_at` |
| `Article.updatedAt` / `ArticleI18n.updatedAt` requis à la création | **`@updatedAt`** sur les champs mappés pour génération côté client |
| Client non régénéré après changement de schéma | **`npx prisma generate`** obligatoire après pull / merge |

Fichiers clés :

- `web/prisma/schema.prisma` — modèles `Article`, `ArticleBlock`, `ArticleBlockI18n`, `ArticleI18n`
- `web/src/lib/blog/articleService.ts` — `getBlogFeed`, `getArticleBySlug` (includes `coverMedia`, `blocks`, `i18n`)

## Data Issues

- **`investment_categories`** vide si seed jamais exécuté sur la base unifiée.
- **`articles`** sans ligne `PUBLISHED` + **`article_i18n`** (locale `fr`) → feed vide.
- **`article_blocks` / `article_block_i18n`** manquants pour un article → prévisualisation / détail dégradés.

## Fix Applied

1. **Schéma Prisma** : relations `ArticleBlock.i18n` / `ArticleBlockI18n.block` ; `@updatedAt` sur `Article`, `ArticleI18n`, `ArticleBlockI18n`.
2. **Instrumentation** :
   - `GET /api/blog` : logs `[api/blog]` avec **cible DB** (host/port/db sans mot de passe), durées, erreurs Prisma (`code`, `meta` si connues).
   - `getBlogFeed` : log **`[blog] prisma query failed`** + **`[blog] blog feed empty`** quand aucun contenu publié ne correspond aux filtres.
3. **Outil diagnostic** : `npm run db:diagnose-blog` → `scripts/diagnose-blog-prisma.ts` (mêmes requêtes que le flux blog + shape `getArticleBySlug`).
4. **Seed idempotent** : article publié `arquantix-bienvenue` (FR + 1 bloc PARAGRAPH + i18n bloc) dans `prisma/seed.ts`.
5. **Health** : `GET /api/health/products` expose désormais **`blog_count`** (articles `PUBLISHED`) et **`db`** (host/port/db).

## Seed Strategy

```bash
cd services/arquantix/web
# ADMIN_SEED_EMAIL / ADMIN_SEED_PASSWORD requis
npx prisma generate
npm run db:seed
```

Le seed existant (admin, home page, menu, catégories d’investissement, types) est **conservé** ; l’article blog est ajouté **uniquement** si le slug `arquantix-bienvenue` n’existe pas.

## Tests

1. **Prisma** : `npm run db:diagnose-blog` (succès, pas d’exception).
2. **HTTP** : `GET /api/blog?locale=fr&page=1&pageSize=20` → **200** et JSON avec `categories`, `articles`, `pagination`.
3. **Health** : `GET /api/health/products` → `blog_count` ≥ 1 après seed.
4. **Flutter** : plus de `BlogApiException(500)` une fois Next à jour (`prisma generate` + même `DATABASE_URL` que l’API).

## DATABASE_URL (rappel)

Next (`web/.env`) et API (`api/.env`) doivent pointer vers **la même** base unifiée. Vérifier via les logs `[api/blog] GET start` / réponse health `db`, ou :

`npm run db:diagnose-blog` (affiche `[Next Prisma DB] host=… port=… db=…`).
