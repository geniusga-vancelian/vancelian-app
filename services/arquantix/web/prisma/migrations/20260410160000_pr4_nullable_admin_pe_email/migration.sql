-- PR4 — aligné sur Alembic 130 : email nullable + index uniques partiels + backfill placeholders.

DROP INDEX IF EXISTS "ix_admin_users_email";
ALTER TABLE "admin_users" ALTER COLUMN "email" DROP NOT NULL;
CREATE UNIQUE INDEX "ix_admin_users_email" ON "admin_users"("email") WHERE "email" IS NOT NULL;

UPDATE "admin_users"
SET "email" = NULL
WHERE "email" IS NOT NULL
  AND (
    lower("email"::text) LIKE '%@signup.internal'
    OR lower("email"::text) LIKE '%@internal'
  );

DROP INDEX IF EXISTS "ix_pe_clients_email";
ALTER TABLE "pe_clients" ALTER COLUMN "email" DROP NOT NULL;
CREATE UNIQUE INDEX "ix_pe_clients_email" ON "pe_clients"("email") WHERE "email" IS NOT NULL;

UPDATE "pe_clients"
SET "email" = NULL
WHERE "email" IS NOT NULL
  AND (
    lower("email"::text) LIKE '%@signup.internal'
    OR lower("email"::text) LIKE '%@internal'
  );
