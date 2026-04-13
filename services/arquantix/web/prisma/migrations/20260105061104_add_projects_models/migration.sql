/*
  Warnings:

  - Made the column `template` on table `pages` required. This step will fail if there are existing NULL values in that column.

*/
-- AlterTable
ALTER TABLE "pages" ALTER COLUMN "template" SET NOT NULL,
ALTER COLUMN "updated_at" DROP DEFAULT;

-- CreateTable
CREATE TABLE "projects" (
    "id" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "status" "ContentStatus" NOT NULL DEFAULT 'DRAFT',
    "cover_media_id" TEXT,
    "youtube_url" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "projects_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "project_i18n" (
    "id" TEXT NOT NULL,
    "project_id" TEXT NOT NULL,
    "locale" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "short_description" TEXT,
    "description" TEXT,
    "meta_title" TEXT,
    "meta_description" TEXT,

    CONSTRAINT "project_i18n_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "project_media" (
    "id" TEXT NOT NULL,
    "project_id" TEXT NOT NULL,
    "media_id" TEXT NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "project_media_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "projects_slug_key" ON "projects"("slug");

-- CreateIndex
CREATE INDEX "project_i18n_project_id_idx" ON "project_i18n"("project_id");

-- CreateIndex
CREATE UNIQUE INDEX "project_i18n_project_id_locale_key" ON "project_i18n"("project_id", "locale");

-- CreateIndex
CREATE INDEX "project_media_project_id_idx" ON "project_media"("project_id");

-- CreateIndex
CREATE UNIQUE INDEX "project_media_project_id_order_key" ON "project_media"("project_id", "order");

-- AddForeignKey
ALTER TABLE "projects" ADD CONSTRAINT "projects_cover_media_id_fkey" FOREIGN KEY ("cover_media_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "project_i18n" ADD CONSTRAINT "project_i18n_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "project_media" ADD CONSTRAINT "project_media_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "project_media" ADD CONSTRAINT "project_media_media_id_fkey" FOREIGN KEY ("media_id") REFERENCES "media"("id") ON DELETE CASCADE ON UPDATE CASCADE;
