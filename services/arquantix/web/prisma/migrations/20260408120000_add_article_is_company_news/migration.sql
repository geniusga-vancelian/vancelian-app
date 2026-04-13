-- Company news flag (explicit; legacy slug `vancelian` remains supported in app code until fully migrated)

ALTER TABLE "articles" ADD COLUMN IF NOT EXISTS "is_company_news" BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS "articles_is_company_news_idx" ON "articles"("is_company_news");

-- Backfill from legacy category slug (NEWS only)
UPDATE "articles"
SET "is_company_news" = true
WHERE "article_type" = 'NEWS'
  AND "category_slugs" IS NOT NULL
  AND "category_slugs"::jsonb @> '["vancelian"]'::jsonb;

-- Safety: non-NEWS editorial types cannot be company news
UPDATE "articles"
SET "is_company_news" = false
WHERE "article_type" IN ('ANALYSIS', 'RESEARCH');
