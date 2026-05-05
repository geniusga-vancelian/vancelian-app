-- Multilingual toggle for public language switcher (admin-configurable).
ALTER TABLE "app_settings" ADD COLUMN "multilingual_enabled" BOOLEAN NOT NULL DEFAULT true;
