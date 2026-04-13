-- AlterTable
ALTER TABLE "investment_categories" ADD COLUMN "description" TEXT;
ALTER TABLE "investment_categories" ADD COLUMN "media_id" TEXT;

-- CreateIndex
CREATE INDEX "investment_categories_media_id_idx" ON "investment_categories"("media_id");

-- AddForeignKey
ALTER TABLE "investment_categories" ADD CONSTRAINT "investment_categories_media_id_fkey" FOREIGN KEY ("media_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;
