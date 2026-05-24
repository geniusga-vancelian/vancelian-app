-- CreateEnum
CREATE TYPE "OnchainVaultOperation" AS ENUM ('deposit', 'withdraw', 'approve');

-- CreateEnum
CREATE TYPE "OnchainVaultTransactionStatus" AS ENUM ('pending', 'success', 'reverted', 'failed');

-- CreateTable
CREATE TABLE "defi_vault_registry" (
    "id" TEXT NOT NULL,
    "chain_id" INTEGER NOT NULL,
    "vault_address" TEXT NOT NULL,
    "morpho_version" TEXT NOT NULL,
    "asset_address" TEXT NOT NULL,
    "asset_symbol" TEXT NOT NULL,
    "asset_decimals" INTEGER NOT NULL DEFAULT 6,
    "name" TEXT,
    "curator" TEXT,
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "defi_vault_registry_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_vault_positions" (
    "id" TEXT NOT NULL,
    "person_id" UUID NOT NULL,
    "vault_address" TEXT NOT NULL,
    "chain_id" INTEGER NOT NULL,
    "wallet_address" TEXT NOT NULL,
    "asset_symbol" TEXT NOT NULL,
    "asset_decimals" INTEGER NOT NULL DEFAULT 6,
    "principal_net_raw" TEXT NOT NULL DEFAULT '0',
    "last_assets_raw" TEXT,
    "last_shares_raw" TEXT,
    "last_synced_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "user_vault_positions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "onchain_vault_transactions" (
    "id" TEXT NOT NULL,
    "person_id" UUID NOT NULL,
    "vault_address" TEXT NOT NULL,
    "chain_id" INTEGER NOT NULL,
    "wallet_address" TEXT NOT NULL,
    "operation" "OnchainVaultOperation" NOT NULL,
    "amount_raw" TEXT NOT NULL,
    "asset_symbol" TEXT NOT NULL,
    "asset_decimals" INTEGER NOT NULL DEFAULT 6,
    "tx_hash" TEXT,
    "status" "OnchainVaultTransactionStatus" NOT NULL DEFAULT 'pending',
    "idempotency_key" TEXT NOT NULL,
    "privy_action_id" TEXT,
    "block_number" BIGINT,
    "integration_mode" TEXT NOT NULL,
    "tx_index" INTEGER NOT NULL DEFAULT 0,
    "group_key" TEXT,
    "error_message" TEXT,
    "metadata_json" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "onchain_vault_transactions_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "defi_vault_registry_chain_vault_key" ON "defi_vault_registry"("chain_id", "vault_address");

-- CreateIndex
CREATE UNIQUE INDEX "user_vault_positions_person_vault_wallet_key" ON "user_vault_positions"("person_id", "chain_id", "vault_address", "wallet_address");

-- CreateIndex
CREATE INDEX "user_vault_positions_person_id_idx" ON "user_vault_positions"("person_id");

-- CreateIndex
CREATE UNIQUE INDEX "onchain_vault_tx_idempotency_key" ON "onchain_vault_transactions"("person_id", "vault_address", "operation", "idempotency_key", "tx_index");

-- CreateIndex
CREATE INDEX "onchain_vault_tx_person_vault_idx" ON "onchain_vault_transactions"("person_id", "vault_address");

-- CreateIndex
CREATE INDEX "onchain_vault_tx_hash_idx" ON "onchain_vault_transactions"("tx_hash");

-- CreateIndex
CREATE INDEX "onchain_vault_tx_status_idx" ON "onchain_vault_transactions"("status");

-- CreateIndex
CREATE INDEX "onchain_vault_tx_group_key_idx" ON "onchain_vault_transactions"("group_key");
