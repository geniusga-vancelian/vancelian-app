-- Product Registry: packaged_products + lien optionnel lending_pool_products
-- Rollback: DROP TABLE packaged_products CASCADE; ALTER lending_pool_products DROP COLUMN packaged_product_id;
-- (détruire les enums seulement si plus aucune table ne les utilise)

CREATE TYPE "PackagedProductType" AS ENUM ('VAULT_SIMPLE', 'EXCLUSIVE_OFFER', 'MANAGED_MANDATE', 'CRYPTO_BUNDLE');

CREATE TYPE "PackagedCommercialStatus" AS ENUM ('DRAFT', 'PUBLISHED', 'ARCHIVED');

CREATE TYPE "PackagedVisibility" AS ENUM ('PUBLIC', 'PRIVATE', 'HIDDEN');

CREATE TYPE "PackagedEngineType" AS ENUM ('LENDING', 'BUNDLE', 'MANAGED_PORTFOLIO', 'VAULT_ENGINE');

CREATE TABLE "packaged_products" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "slug" TEXT NOT NULL,
    "page_id" TEXT NOT NULL,
    "product_type" "PackagedProductType" NOT NULL,
    "commercial_status" "PackagedCommercialStatus" NOT NULL,
    "visibility" "PackagedVisibility" NOT NULL,
    "featured_rank" INTEGER,
    "category_slug" TEXT,
    "tags" JSONB,
    "engine_type" "PackagedEngineType",
    "engine_reference_id" VARCHAR(255),
    "legacy_project_id" TEXT,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "published_at" TIMESTAMPTZ(6),

    CONSTRAINT "packaged_products_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "packaged_products_slug_key" ON "packaged_products"("slug");

CREATE UNIQUE INDEX "packaged_products_page_id_key" ON "packaged_products"("page_id");

CREATE UNIQUE INDEX "packaged_products_legacy_project_id_key" ON "packaged_products"("legacy_project_id");

CREATE INDEX "ix_packaged_products_product_type" ON "packaged_products"("product_type");

CREATE INDEX "ix_packaged_products_visibility" ON "packaged_products"("visibility");

CREATE INDEX "ix_packaged_products_commercial_status" ON "packaged_products"("commercial_status");

CREATE INDEX "ix_packaged_products_type_featured" ON "packaged_products"("product_type", "featured_rank");

ALTER TABLE "packaged_products" ADD CONSTRAINT "packaged_products_page_id_fkey" FOREIGN KEY ("page_id") REFERENCES "pages"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "packaged_products" ADD CONSTRAINT "packaged_products_legacy_project_id_fkey" FOREIGN KEY ("legacy_project_id") REFERENCES "projects"("id") ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE "lending_pool_products" ADD COLUMN "packaged_product_id" UUID;

CREATE UNIQUE INDEX "lending_pool_products_packaged_product_id_key" ON "lending_pool_products"("packaged_product_id");

ALTER TABLE "lending_pool_products" ADD CONSTRAINT "lending_pool_products_packaged_product_id_fkey" FOREIGN KEY ("packaged_product_id") REFERENCES "packaged_products"("id") ON DELETE SET NULL ON UPDATE CASCADE;
