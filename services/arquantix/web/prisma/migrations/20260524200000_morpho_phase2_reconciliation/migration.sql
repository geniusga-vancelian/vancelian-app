-- CreateEnum
CREATE TYPE "MorphoReconciliationStatus" AS ENUM ('matched', 'mismatch', 'missing_onchain', 'missing_ledger');

-- AlterTable defi_vault_registry
ALTER TABLE "defi_vault_registry" ADD COLUMN "integration_mode" TEXT;
ALTER TABLE "defi_vault_registry" ADD COLUMN "privy_vault_id" TEXT;
ALTER TABLE "defi_vault_registry" ADD COLUMN "portal_config_id" TEXT;
ALTER TABLE "defi_vault_registry" ADD COLUMN "last_synced_at" TIMESTAMP(3);

-- AlterTable user_vault_positions
ALTER TABLE "user_vault_positions" ADD COLUMN "chain_type" TEXT NOT NULL DEFAULT 'evm';
ALTER TABLE "user_vault_positions" ADD COLUMN "privy_wallet_id" TEXT;
ALTER TABLE "user_vault_positions" ADD COLUMN "cost_basis_unknown" BOOLEAN NOT NULL DEFAULT false;

-- AlterTable onchain_vault_transactions
ALTER TABLE "onchain_vault_transactions" ADD COLUMN "chain_type" TEXT NOT NULL DEFAULT 'evm';
ALTER TABLE "onchain_vault_transactions" ADD COLUMN "privy_wallet_id" TEXT;

-- CreateIndex
CREATE INDEX "user_vault_positions_privy_wallet_id_idx" ON "user_vault_positions"("privy_wallet_id");
CREATE INDEX "onchain_vault_tx_privy_wallet_id_idx" ON "onchain_vault_transactions"("privy_wallet_id");
CREATE INDEX "defi_vault_registry_portal_config_id_idx" ON "defi_vault_registry"("portal_config_id");

-- CreateTable morpho_vault_reconciliation_runs
CREATE TABLE "morpho_vault_reconciliation_runs" (
    "id" TEXT NOT NULL,
    "started_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "finished_at" TIMESTAMP(3),
    "items_checked" INTEGER NOT NULL DEFAULT 0,
    "matched_count" INTEGER NOT NULL DEFAULT 0,
    "mismatch_count" INTEGER NOT NULL DEFAULT 0,
    "missing_onchain_count" INTEGER NOT NULL DEFAULT 0,
    "missing_ledger_count" INTEGER NOT NULL DEFAULT 0,
    "log_json" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "morpho_vault_reconciliation_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable morpho_vault_reconciliation_items
CREATE TABLE "morpho_vault_reconciliation_items" (
    "id" TEXT NOT NULL,
    "run_id" TEXT NOT NULL,
    "person_id" UUID NOT NULL,
    "vault_address" TEXT NOT NULL,
    "wallet_address" TEXT NOT NULL,
    "privy_wallet_id" TEXT,
    "integration_mode" TEXT NOT NULL,
    "status" "MorphoReconciliationStatus" NOT NULL,
    "ledger_assets_raw" TEXT,
    "onchain_assets_raw" TEXT,
    "delta_assets_raw" TEXT,
    "ledger_shares_raw" TEXT,
    "onchain_shares_raw" TEXT,
    "delta_shares_raw" TEXT,
    "details_json" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "morpho_vault_reconciliation_items_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "morpho_reconciliation_items_run_id_idx" ON "morpho_vault_reconciliation_items"("run_id");
CREATE INDEX "morpho_reconciliation_items_status_idx" ON "morpho_vault_reconciliation_items"("status");
CREATE INDEX "morpho_reconciliation_items_person_id_idx" ON "morpho_vault_reconciliation_items"("person_id");

-- AddForeignKey
ALTER TABLE "morpho_vault_reconciliation_items" ADD CONSTRAINT "morpho_vault_reconciliation_items_run_id_fkey" FOREIGN KEY ("run_id") REFERENCES "morpho_vault_reconciliation_runs"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- Backfill privy_wallet_id from legacy rows where wallet_address stored Privy ID
UPDATE "onchain_vault_transactions"
SET "privy_wallet_id" = "wallet_address"
WHERE "integration_mode" = 'privy_earn'
  AND "privy_wallet_id" IS NULL
  AND "wallet_address" NOT LIKE '0x%';

UPDATE "user_vault_positions" AS uvp
SET "privy_wallet_id" = uvp."wallet_address"
FROM (
  SELECT id, wallet_address
  FROM "user_vault_positions"
  WHERE wallet_address NOT LIKE '0x%'
) AS legacy
WHERE uvp.id = legacy.id
  AND uvp."privy_wallet_id" IS NULL;

-- Backfill EVM wallet_address from person_crypto_wallets metadata when possible
UPDATE "onchain_vault_transactions" AS ovt
SET "wallet_address" = lower(pcw.address)
FROM "person_crypto_wallets" AS pcw
WHERE ovt."person_id" = pcw."person_id"
  AND pcw."revoked_at" IS NULL
  AND pcw."chain_type" = 'ethereum'
  AND ovt."wallet_address" NOT LIKE '0x%'
  AND (
    (pcw.metadata_json->>'privy_wallet_id') = ovt."wallet_address"
    OR (pcw.metadata_json->>'privyWalletId') = ovt."wallet_address"
  );

UPDATE "user_vault_positions" AS uvp
SET "wallet_address" = lower(pcw.address)
FROM "person_crypto_wallets" AS pcw
WHERE uvp."person_id" = pcw."person_id"
  AND pcw."revoked_at" IS NULL
  AND pcw."chain_type" = 'ethereum'
  AND uvp."wallet_address" NOT LIKE '0x%'
  AND (
    (pcw.metadata_json->>'privy_wallet_id') = uvp."wallet_address"
    OR (pcw.metadata_json->>'privyWalletId') = uvp."wallet_address"
  );
