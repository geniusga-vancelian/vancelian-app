-- CmsUiString: overrides CMS pour les strings ARB Flutter.
-- Permet à l'admin de redéfinir un texte UI (bouton "Investir", titre de
-- module natif, etc.) par locale et statut DRAFT/PUBLISHED, sans rebuild
-- de l'app Flutter. Bundle public exposé via /api/mobile/flutter/ui-strings.

CREATE TABLE IF NOT EXISTS "cms_ui_strings" (
    "id"                 TEXT            NOT NULL,
    "key"                TEXT            NOT NULL,
    "namespace"          TEXT            NOT NULL,
    "locale"             TEXT            NOT NULL,
    "value"              TEXT            NOT NULL,
    "sourceText"         TEXT,
    "description"        TEXT,
    "placeholders"       JSONB,
    "status"             "ContentStatus" NOT NULL,
    "translation_status" "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL',
    "source"             TEXT            NOT NULL DEFAULT 'arb_extract',
    "updated_at"         TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "created_at"         TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_by_user_id" TEXT,

    CONSTRAINT "cms_ui_strings_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "cms_ui_strings_key_locale_status_key"
    ON "cms_ui_strings"("key", "locale", "status");

CREATE INDEX IF NOT EXISTS "cms_ui_strings_namespace_locale_status_idx"
    ON "cms_ui_strings"("namespace", "locale", "status");

CREATE INDEX IF NOT EXISTS "cms_ui_strings_locale_status_idx"
    ON "cms_ui_strings"("locale", "status");

CREATE INDEX IF NOT EXISTS "cms_ui_strings_key_idx"
    ON "cms_ui_strings"("key");

ALTER TABLE "cms_ui_strings"
    ADD CONSTRAINT "cms_ui_strings_updated_by_user_id_fkey"
    FOREIGN KEY ("updated_by_user_id") REFERENCES "users"("id")
    ON DELETE SET NULL ON UPDATE CASCADE;
