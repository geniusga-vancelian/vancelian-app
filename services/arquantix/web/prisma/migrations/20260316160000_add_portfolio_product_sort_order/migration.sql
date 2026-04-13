-- Add sort_order column to portfolio_product_configs for controlling display order of bundles
ALTER TABLE "portfolio_product_configs" ADD COLUMN "sort_order" INTEGER NOT NULL DEFAULT 999;

CREATE INDEX "portfolio_product_configs_sort_order_idx" ON "portfolio_product_configs"("sort_order");
