-- CreateTable
CREATE TABLE "app_settings" (
    "id" TEXT NOT NULL,
    "supported_locales" TEXT NOT NULL DEFAULT '["fr","en","ar","it"]',
    "default_locale" TEXT NOT NULL DEFAULT 'fr',
    "translation_glossary" JSONB,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "app_settings_pkey" PRIMARY KEY ("id")
);

-- Insert default settings
INSERT INTO "app_settings" ("id", "supported_locales", "default_locale", "translation_glossary", "updated_at")
VALUES ('default', '["fr","en","ar","it"]', 'fr', NULL, NOW());









