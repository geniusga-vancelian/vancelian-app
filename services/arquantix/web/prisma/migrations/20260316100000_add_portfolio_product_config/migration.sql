-- CreateTable
CREATE TABLE "portfolio_product_configs" (
    "id" TEXT NOT NULL,
    "product_code" TEXT NOT NULL,
    "modules" JSONB NOT NULL DEFAULT '[]',
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "portfolio_product_configs_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "portfolio_product_configs_product_code_key" ON "portfolio_product_configs"("product_code");
