-- AlterTable
ALTER TABLE "projects" ADD COLUMN     "hero_media_id" TEXT;

-- AddForeignKey
ALTER TABLE "projects" ADD CONSTRAINT "projects_hero_media_id_fkey" FOREIGN KEY ("hero_media_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;
