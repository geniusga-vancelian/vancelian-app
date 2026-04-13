-- CreateTable
CREATE TABLE "investment_categories" (
    "id" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "label" TEXT NOT NULL,
    "image_url" TEXT,
    "sort_order" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "investment_categories_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "investment_categories_slug_key" ON "investment_categories"("slug");

-- CreateIndex
CREATE INDEX "investment_categories_sort_order_idx" ON "investment_categories"("sort_order");
