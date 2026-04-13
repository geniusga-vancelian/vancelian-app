-- CreateTable
CREATE TABLE "menu_item_i18n" (
    "id" TEXT NOT NULL,
    "menu_item_id" TEXT NOT NULL,
    "locale" TEXT NOT NULL,
    "label" TEXT NOT NULL,
    "translation_status" "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "menu_item_i18n_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "article_category_i18n" (
    "id" TEXT NOT NULL,
    "category_id" TEXT NOT NULL,
    "locale" TEXT NOT NULL,
    "label" TEXT NOT NULL,
    "translation_status" "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "article_category_i18n_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "menu_item_i18n_menu_item_id_locale_key" ON "menu_item_i18n"("menu_item_id", "locale");

-- CreateIndex
CREATE INDEX "menu_item_i18n_menu_item_id_idx" ON "menu_item_i18n"("menu_item_id");

-- CreateIndex
CREATE INDEX "menu_item_i18n_locale_idx" ON "menu_item_i18n"("locale");

-- CreateIndex
CREATE UNIQUE INDEX "article_category_i18n_category_id_locale_key" ON "article_category_i18n"("category_id", "locale");

-- CreateIndex
CREATE INDEX "article_category_i18n_category_id_idx" ON "article_category_i18n"("category_id");

-- CreateIndex
CREATE INDEX "article_category_i18n_locale_idx" ON "article_category_i18n"("locale");

-- AddForeignKey
ALTER TABLE "menu_item_i18n" ADD CONSTRAINT "menu_item_i18n_menu_item_id_fkey" FOREIGN KEY ("menu_item_id") REFERENCES "menu_items"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "article_category_i18n" ADD CONSTRAINT "article_category_i18n_category_id_fkey" FOREIGN KEY ("category_id") REFERENCES "article_categories"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- Data migration: Copy existing labels to i18n tables for default locale (fr)
INSERT INTO "menu_item_i18n" ("id", "menu_item_id", "locale", "label", "translation_status", "created_at", "updated_at")
SELECT 
    gen_random_uuid()::text as id,
    id as menu_item_id,
    'fr' as locale,
    label,
    'ORIGINAL' as translation_status,
    NOW() as created_at,
    NOW() as updated_at
FROM "menu_items"
WHERE NOT EXISTS (
    SELECT 1 FROM "menu_item_i18n" WHERE "menu_item_i18n"."menu_item_id" = "menu_items"."id" AND "menu_item_i18n"."locale" = 'fr'
);

INSERT INTO "article_category_i18n" ("id", "category_id", "locale", "label", "translation_status", "created_at", "updated_at")
SELECT 
    gen_random_uuid()::text as id,
    id as category_id,
    'fr' as locale,
    label,
    'ORIGINAL' as translation_status,
    NOW() as created_at,
    NOW() as updated_at
FROM "article_categories"
WHERE NOT EXISTS (
    SELECT 1 FROM "article_category_i18n" WHERE "article_category_i18n"."category_id" = "article_categories"."id" AND "article_category_i18n"."locale" = 'fr'
);









