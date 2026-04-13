-- CreateTable
CREATE TABLE IF NOT EXISTS "investment_types" (
    "id" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "label" TEXT NOT NULL,
    "description" TEXT,
    "color_hex" TEXT NOT NULL DEFAULT '#6366F1',
    "icon_key" TEXT NOT NULL DEFAULT 'tag',
    "sort_order" INTEGER NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "investment_types_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX IF NOT EXISTS "investment_types_slug_key" ON "investment_types"("slug");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "investment_types_sort_order_idx" ON "investment_types"("sort_order");
