-- Phase 4 — Academy : hiérarchie collection/catégorie symétrique au Centre d'aide.
-- ADD-only, idempotent (CREATE IF NOT EXISTS, ALTER ADD COLUMN IF NOT EXISTS, FK
-- guards sur pg_constraint, ajout d'enum gardé sur pg_enum). Aucun rename, drop,
-- ni changement de port/conteneur/.env.
--
-- Articles ACADEMY : Article(articleType='ACADEMY') existe déjà ; on ajoute
-- juste les FK academy_collection_id / academy_category_id / academy_slug pour
-- la hiérarchie. Pas d'AcademyArticle legacy : démarrage direct sur Article unifié.

-- ─────────────────────────────────────────────────────────────────────────────
--  1. Tables academy_*
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS "academy_collections" (
    "id" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "icon_key" TEXT NOT NULL DEFAULT 'school',
    "color_hex" TEXT NOT NULL DEFAULT '#0F172A',
    "order" INTEGER NOT NULL DEFAULT 0,
    "is_published" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "academy_collections_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "academy_collections_slug_key" ON "academy_collections"("slug");

CREATE TABLE IF NOT EXISTS "academy_collection_i18n" (
    "id" TEXT NOT NULL,
    "collection_id" TEXT NOT NULL,
    "locale" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "subtitle" TEXT,
    "description" TEXT,
    "translation_status" "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "academy_collection_i18n_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "academy_collection_i18n_collection_id_locale_key"
    ON "academy_collection_i18n"("collection_id", "locale");

CREATE TABLE IF NOT EXISTS "academy_categories" (
    "id" TEXT NOT NULL,
    "collection_id" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    "is_published" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "academy_categories_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "academy_categories_collection_id_slug_key"
    ON "academy_categories"("collection_id", "slug");
CREATE INDEX IF NOT EXISTS "academy_categories_collection_id_idx"
    ON "academy_categories"("collection_id");

CREATE TABLE IF NOT EXISTS "academy_category_i18n" (
    "id" TEXT NOT NULL,
    "category_id" TEXT NOT NULL,
    "locale" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "description" TEXT,
    "translation_status" "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "academy_category_i18n_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "academy_category_i18n_category_id_locale_key"
    ON "academy_category_i18n"("category_id", "locale");

-- ─────────────────────────────────────────────────────────────────────────────
--  2. Foreign keys academy_* (idempotent)
-- ─────────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'academy_collection_i18n_collection_id_fkey'
  ) THEN
    ALTER TABLE "academy_collection_i18n"
      ADD CONSTRAINT "academy_collection_i18n_collection_id_fkey"
      FOREIGN KEY ("collection_id") REFERENCES "academy_collections"("id")
      ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'academy_categories_collection_id_fkey'
  ) THEN
    ALTER TABLE "academy_categories"
      ADD CONSTRAINT "academy_categories_collection_id_fkey"
      FOREIGN KEY ("collection_id") REFERENCES "academy_collections"("id")
      ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'academy_category_i18n_category_id_fkey'
  ) THEN
    ALTER TABLE "academy_category_i18n"
      ADD CONSTRAINT "academy_category_i18n_category_id_fkey"
      FOREIGN KEY ("category_id") REFERENCES "academy_categories"("id")
      ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
--  3. Colonnes academy_* sur articles + index + unique + FK
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE "articles" ADD COLUMN IF NOT EXISTS "academy_collection_id" TEXT;
ALTER TABLE "articles" ADD COLUMN IF NOT EXISTS "academy_category_id"   TEXT;
ALTER TABLE "articles" ADD COLUMN IF NOT EXISTS "academy_slug"          TEXT;

CREATE INDEX IF NOT EXISTS "articles_academy_collection_id_idx"
    ON "articles"("academy_collection_id");
CREATE INDEX IF NOT EXISTS "articles_academy_category_id_idx"
    ON "articles"("academy_category_id");
CREATE UNIQUE INDEX IF NOT EXISTS "uq_articles_academy_category_academy_slug"
    ON "articles"("academy_category_id", "academy_slug");

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'articles_academy_collection_id_fkey'
  ) THEN
    ALTER TABLE "articles"
      ADD CONSTRAINT "articles_academy_collection_id_fkey"
      FOREIGN KEY ("academy_collection_id") REFERENCES "academy_collections"("id")
      ON DELETE RESTRICT ON UPDATE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'articles_academy_category_id_fkey'
  ) THEN
    ALTER TABLE "articles"
      ADD CONSTRAINT "articles_academy_category_id_fkey"
      FOREIGN KEY ("academy_category_id") REFERENCES "academy_categories"("id")
      ON DELETE RESTRICT ON UPDATE CASCADE;
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
--  4. Enum TranslationEntityType : ajouter ACADEMY_*
-- ─────────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_enum
    WHERE enumlabel = 'ACADEMY_COLLECTION'
      AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'TranslationEntityType')
  ) THEN
    ALTER TYPE "TranslationEntityType" ADD VALUE 'ACADEMY_COLLECTION';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_enum
    WHERE enumlabel = 'ACADEMY_CATEGORY'
      AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'TranslationEntityType')
  ) THEN
    ALTER TYPE "TranslationEntityType" ADD VALUE 'ACADEMY_CATEGORY';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_enum
    WHERE enumlabel = 'ACADEMY_ARTICLE'
      AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'TranslationEntityType')
  ) THEN
    ALTER TYPE "TranslationEntityType" ADD VALUE 'ACADEMY_ARTICLE';
  END IF;
END $$;
