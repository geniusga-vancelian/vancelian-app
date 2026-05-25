-- CreateEnum
CREATE TYPE "LedgityReconciliationStatus" AS ENUM ('matched', 'mismatch', 'missing_onchain', 'missing_ledger', 'pps_unavailable', 'liquidity_warning');

-- CreateTable
CREATE TABLE "ledgity_vault_reconciliation_runs" (
    "id" TEXT NOT NULL,
    "started_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "finished_at" TIMESTAMP(3),
    "items_checked" INTEGER NOT NULL DEFAULT 0,
    "matched_count" INTEGER NOT NULL DEFAULT 0,
    "mismatch_count" INTEGER NOT NULL DEFAULT 0,
    "missing_onchain_count" INTEGER NOT NULL DEFAULT 0,
    "missing_ledger_count" INTEGER NOT NULL DEFAULT 0,
    "pps_unavailable_count" INTEGER NOT NULL DEFAULT 0,
    "liquidity_warning_count" INTEGER NOT NULL DEFAULT 0,
    "log_json" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ledgity_vault_reconciliation_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ledgity_vault_reconciliation_items" (
    "id" TEXT NOT NULL,
    "run_id" TEXT NOT NULL,
    "person_id" UUID NOT NULL,
    "vault_address" TEXT NOT NULL,
    "wallet_address" TEXT NOT NULL,
    "privy_wallet_id" TEXT,
    "integration_mode" TEXT NOT NULL DEFAULT 'ledgity_vault',
    "status" "LedgityReconciliationStatus" NOT NULL,
    "ledger_assets_raw" TEXT,
    "onchain_assets_raw" TEXT,
    "delta_assets_raw" TEXT,
    "ledger_shares_raw" TEXT,
    "onchain_shares_raw" TEXT,
    "delta_shares_raw" TEXT,
    "pps_at_reconcile" TEXT,
    "details_json" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ledgity_vault_reconciliation_items_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "ledgity_reconciliation_items_run_id_idx" ON "ledgity_vault_reconciliation_items"("run_id");

-- CreateIndex
CREATE INDEX "ledgity_reconciliation_items_status_idx" ON "ledgity_vault_reconciliation_items"("status");

-- CreateIndex
CREATE INDEX "ledgity_reconciliation_items_person_id_idx" ON "ledgity_vault_reconciliation_items"("person_id");

-- AddForeignKey
ALTER TABLE "ledgity_vault_reconciliation_items" ADD CONSTRAINT "ledgity_vault_reconciliation_items_run_id_fkey" FOREIGN KEY ("run_id") REFERENCES "ledgity_vault_reconciliation_runs"("id") ON DELETE CASCADE ON UPDATE NO ACTION;
