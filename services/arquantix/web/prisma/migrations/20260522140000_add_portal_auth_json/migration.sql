-- AlterTable
ALTER TABLE "global_settings" ADD COLUMN IF NOT EXISTS "portal_auth_json" JSONB;
