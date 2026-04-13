-- CreateTable
CREATE TABLE "menu_i18n" (
    "id" TEXT NOT NULL,
    "menu_id" TEXT NOT NULL,
    "locale" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "translation_status" "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "menu_i18n_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "menu_i18n_menu_id_locale_key" ON "menu_i18n"("menu_id", "locale");

-- CreateIndex
CREATE INDEX "menu_i18n_menu_id_idx" ON "menu_i18n"("menu_id");

-- CreateIndex
CREATE INDEX "menu_i18n_locale_idx" ON "menu_i18n"("locale");

-- AddForeignKey
ALTER TABLE "menu_i18n" ADD CONSTRAINT "menu_i18n_menu_id_fkey" FOREIGN KEY ("menu_id") REFERENCES "menus"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- Data migration: Copy existing menu names to i18n table for default locale (fr)
INSERT INTO "menu_i18n" ("id", "menu_id", "locale", "name", "translation_status", "created_at", "updated_at")
SELECT 
    gen_random_uuid()::text as id,
    id as menu_id,
    'fr' as locale,
    name,
    'ORIGINAL' as translation_status,
    NOW() as created_at,
    NOW() as updated_at
FROM "menus"
WHERE NOT EXISTS (
    SELECT 1 FROM "menu_i18n" WHERE "menu_i18n"."menu_id" = "menus"."id" AND "menu_i18n"."locale" = 'fr'
);









