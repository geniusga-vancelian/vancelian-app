ALTER TABLE "project_i18n"
ADD COLUMN IF NOT EXISTS "how_it_works" JSONB;

-- Backfill from existing description so old content keeps showing.
UPDATE "project_i18n"
SET "how_it_works" = jsonb_build_object(
  'title', 'How it works',
  'content', "description",
  'links', '[]'::jsonb
)
WHERE "how_it_works" IS NULL
  AND "description" IS NOT NULL
  AND length(trim("description")) > 0;
