-- CreateEnum
CREATE TYPE "PortalMorphoIntegrationMode" AS ENUM ('direct_morpho', 'privy_earn');

-- CreateTable
CREATE TABLE "portal_morpho_vault_configs" (
    "id" TEXT NOT NULL,
    "vault_address" TEXT NOT NULL,
    "chain_id" INTEGER NOT NULL DEFAULT 8453,
    "integration_mode" "PortalMorphoIntegrationMode" NOT NULL,
    "privy_vault_id" TEXT,
    "label" TEXT,
    "description" TEXT,
    "curator" TEXT,
    "sort_order" INTEGER NOT NULL DEFAULT 999,
    "is_published" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "portal_morpho_vault_configs_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "portal_morpho_vault_configs_vault_address_key" ON "portal_morpho_vault_configs"("vault_address");

-- CreateIndex
CREATE INDEX "portal_morpho_vault_configs_sort_order_idx" ON "portal_morpho_vault_configs"("sort_order");

-- CreateIndex
CREATE INDEX "portal_morpho_vault_configs_is_published_idx" ON "portal_morpho_vault_configs"("is_published");

-- Seed: vault Privy Earn Steakhouse Prime USDC (Base)
INSERT INTO "portal_morpho_vault_configs" (
    "id",
    "vault_address",
    "chain_id",
    "integration_mode",
    "privy_vault_id",
    "label",
    "description",
    "sort_order",
    "is_published",
    "updated_at"
) VALUES (
    'seed-steakhouse-prime-usdc',
    '0xBEEFE94c8aD530842bfE7d8B397938fFc1cb83b2',
    8453,
    'privy_earn',
    'svbeyhtpw8317205byhv04ns',
    'Steakhouse Prime USDC',
    'Vault Morpho USDC — rendement on-chain via Privy Earn.',
    0,
    true,
    CURRENT_TIMESTAMP
) ON CONFLICT ("vault_address") DO NOTHING;
