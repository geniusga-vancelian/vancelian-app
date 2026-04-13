-- AlterTable
ALTER TABLE "articles" ADD COLUMN "gallery_media_ids" JSONB;
ALTER TABLE "articles" ADD COLUMN "video_url" TEXT;
ALTER TABLE "articles" ADD COLUMN "category_slugs" JSONB;
ALTER TABLE "articles" ADD COLUMN "documents" JSONB;

-- CreateTable
CREATE TABLE "article_projects" (
    "id" TEXT NOT NULL,
    "article_id" TEXT NOT NULL,
    "project_id" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "article_projects_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "article_categories" (
    "id" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "label" TEXT NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "article_categories_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "article_projects_article_id_project_id_key" ON "article_projects"("article_id", "project_id");

-- CreateIndex
CREATE INDEX "article_projects_project_id_idx" ON "article_projects"("project_id");

-- CreateIndex
CREATE INDEX "article_projects_article_id_idx" ON "article_projects"("article_id");

-- CreateIndex
CREATE UNIQUE INDEX "article_categories_slug_key" ON "article_categories"("slug");

-- CreateIndex
CREATE INDEX "article_categories_slug_idx" ON "article_categories"("slug");

-- CreateIndex
CREATE INDEX "article_categories_is_active_order_idx" ON "article_categories"("is_active", "order");

-- AddForeignKey
ALTER TABLE "article_projects" ADD CONSTRAINT "article_projects_article_id_fkey" FOREIGN KEY ("article_id") REFERENCES "articles"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "article_projects" ADD CONSTRAINT "article_projects_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- Seed initial article categories
INSERT INTO "article_categories" ("id", "slug", "label", "order", "is_active", "created_at", "updated_at") VALUES
('cat1', 'market-insights', 'Market Insights', 0, true, NOW(), NOW()),
('cat2', 'crypto-digital-assets', 'Crypto & Digital Assets', 1, true, NOW(), NOW()),
('cat3', 'macro-allocation', 'Macro Allocation', 2, true, NOW(), NOW()),
('cat4', 'regulation', 'Regulation', 3, true, NOW(), NOW()),
('cat5', 'technology', 'Technology', 4, true, NOW(), NOW()),
('cat6', 'arquantix-research', 'Arquantix Research', 5, true, NOW(), NOW()),
('cat7', 'opinion', 'Opinion', 6, true, NOW(), NOW())
ON CONFLICT ("slug") DO NOTHING;









