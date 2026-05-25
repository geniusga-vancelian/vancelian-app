-- CreateTable
CREATE TABLE "portal_external_wallet_nonces" (
    "id" TEXT NOT NULL,
    "person_id" UUID NOT NULL,
    "nonce" TEXT NOT NULL,
    "expires_at" TIMESTAMPTZ(6) NOT NULL,
    "used_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "portal_external_wallet_nonces_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "portal_ext_wallet_nonce_person_idx" ON "portal_external_wallet_nonces"("person_id");

-- CreateIndex
CREATE INDEX "portal_ext_wallet_nonce_expires_idx" ON "portal_external_wallet_nonces"("expires_at");

-- CreateIndex
CREATE UNIQUE INDEX "portal_ext_wallet_nonce_person_nonce" ON "portal_external_wallet_nonces"("person_id", "nonce");
