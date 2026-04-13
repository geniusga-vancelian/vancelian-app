-- AlterTable
ALTER TABLE "pages" ADD COLUMN     "url_path" TEXT,
ADD COLUMN     "title" TEXT,
ADD COLUMN     "template" TEXT DEFAULT 'homepage',
ADD COLUMN     "description" TEXT,
ADD COLUMN     "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Update existing rows: set url_path based on slug
UPDATE "pages" SET "url_path" = CASE WHEN "slug" = 'home' THEN '/' ELSE '/' || "slug" END;

-- Now make url_path NOT NULL and unique
ALTER TABLE "pages" ALTER COLUMN "url_path" SET NOT NULL;

-- CreateIndex
CREATE UNIQUE INDEX "pages_url_path_key" ON "pages"("url_path");
