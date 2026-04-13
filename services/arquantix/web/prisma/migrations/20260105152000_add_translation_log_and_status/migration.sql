-- CreateEnum
CREATE TYPE "TranslationStatus" AS ENUM ('ORIGINAL', 'MACHINE', 'APPROVED');

-- CreateEnum
CREATE TYPE "TranslationEntityType" AS ENUM ('SECTION', 'PROJECT', 'ARTICLE');

-- CreateEnum
CREATE TYPE "TranslationLogStatus" AS ENUM ('SUCCESS', 'ERROR', 'SKIPPED');

-- AlterTable
ALTER TABLE "section_contents" ADD COLUMN "translation_status" "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL';

-- AlterTable
ALTER TABLE "project_i18n" ADD COLUMN "translation_status" "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL';

-- CreateTable
CREATE TABLE "translation_logs" (
    "id" TEXT NOT NULL,
    "entity_type" "TranslationEntityType" NOT NULL,
    "entity_id" TEXT NOT NULL,
    "source_locale" TEXT NOT NULL,
    "target_locale" TEXT NOT NULL,
    "mode" TEXT NOT NULL,
    "status" "TranslationLogStatus" NOT NULL,
    "model" TEXT NOT NULL,
    "error_message" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "translation_logs_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "translation_logs_entity_type_entity_id_idx" ON "translation_logs"("entity_type", "entity_id");

-- CreateIndex
CREATE INDEX "translation_logs_target_locale_idx" ON "translation_logs"("target_locale");

-- CreateIndex
CREATE INDEX "translation_logs_status_idx" ON "translation_logs"("status");

-- CreateIndex
CREATE INDEX "translation_logs_created_at_idx" ON "translation_logs"("created_at");









