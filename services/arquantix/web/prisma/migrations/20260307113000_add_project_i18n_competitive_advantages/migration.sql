ALTER TABLE "project_i18n"
ADD COLUMN IF NOT EXISTS "competitive_advantages" JSONB;

-- Backfill localized content from the legacy project-level field when missing.
UPDATE "project_i18n" pi
SET "competitive_advantages" = p."competitive_advantages"
FROM "projects" p
WHERE pi."project_id" = p."id"
  AND pi."competitive_advantages" IS NULL
  AND p."competitive_advantages" IS NOT NULL;
