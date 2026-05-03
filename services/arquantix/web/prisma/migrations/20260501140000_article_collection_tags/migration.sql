-- Tags de regroupement « au-dessus » des articles (collection → articles à plat).
ALTER TABLE "articles" ADD COLUMN IF NOT EXISTS "collection_tags" JSONB NOT NULL DEFAULT '[]'::jsonb;

-- Conserver les anciennes données : premier tag = slug de catégorie Help / Academy si défini.
UPDATE "articles" a
SET "collection_tags" = to_jsonb(ARRAY[hc.slug])
FROM "help_categories" hc
WHERE a.help_category_id = hc.id
  AND a.article_type = 'HELP';

UPDATE "articles" a
SET "collection_tags" = to_jsonb(ARRAY[ac.slug])
FROM "academy_categories" ac
WHERE a.academy_category_id = ac.id
  AND a.article_type = 'ACADEMY';

-- Unicité article Help par (collection, help_slug) au lieu de (catégorie, help_slug).
ALTER TABLE "articles" DROP CONSTRAINT IF EXISTS "uq_articles_help_category_help_slug";

CREATE UNIQUE INDEX IF NOT EXISTS "uq_articles_help_collection_help_slug"
ON "articles" ("help_collection_id", "help_slug")
WHERE article_type = 'HELP' AND help_collection_id IS NOT NULL AND help_slug IS NOT NULL;

ALTER TABLE "articles" DROP CONSTRAINT IF EXISTS "uq_articles_academy_category_academy_slug";

CREATE UNIQUE INDEX IF NOT EXISTS "uq_articles_academy_collection_academy_slug"
ON "articles" ("academy_collection_id", "academy_slug")
WHERE article_type = 'ACADEMY' AND academy_collection_id IS NOT NULL AND academy_slug IS NOT NULL;
