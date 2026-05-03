-- Modules communs globaux (réutilisables sur les pages CMS via section `common_module_ref`).
ALTER TABLE "global_settings" ADD COLUMN IF NOT EXISTS "common_modules_json" JSONB;
