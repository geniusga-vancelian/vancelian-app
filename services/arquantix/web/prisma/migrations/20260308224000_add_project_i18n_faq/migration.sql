-- AlterTable
ALTER TABLE "project_i18n"
ADD COLUMN IF NOT EXISTS "faq" JSONB;
