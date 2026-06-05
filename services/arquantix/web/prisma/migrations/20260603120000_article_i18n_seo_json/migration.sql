-- SEO étendu par locale (focus_keywords, og_*, named_entities, sources, etc.)
ALTER TABLE "article_i18n"
ADD COLUMN IF NOT EXISTS "seo_json" JSONB NOT NULL DEFAULT '{}';
