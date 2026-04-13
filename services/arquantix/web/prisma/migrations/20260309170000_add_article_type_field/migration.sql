-- Add article type to distinguish news vs analysis.
ALTER TABLE "articles"
ADD COLUMN IF NOT EXISTS "article_type" TEXT NOT NULL DEFAULT 'NEWS';

-- Restrict possible values at DB level.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'articles_article_type_check'
  ) THEN
    ALTER TABLE "articles"
    ADD CONSTRAINT "articles_article_type_check"
    CHECK ("article_type" IN ('NEWS', 'ANALYSIS'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS "articles_article_type_idx"
ON "articles"("article_type");
