-- Add is_published column to portfolio_product_configs for controlling visibility in frontends
ALTER TABLE "portfolio_product_configs" ADD COLUMN "is_published" BOOLEAN NOT NULL DEFAULT false;
