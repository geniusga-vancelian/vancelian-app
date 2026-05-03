-- Tables Help Center : absentes de l’historique Prisma (seuls des ALTER conditionnels existaient).
-- Crée l’ensemble du schéma aligné sur `HelpCollection` … `HelpArticleBlock` (schema.prisma).

CREATE TABLE IF NOT EXISTS "help_collections" (
    "id" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "icon_key" TEXT NOT NULL DEFAULT 'article',
    "color_hex" TEXT NOT NULL DEFAULT '#0F172A',
    "order" INTEGER NOT NULL DEFAULT 0,
    "is_published" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "help_collections_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "help_collections_slug_key" ON "help_collections"("slug");

CREATE TABLE IF NOT EXISTS "help_collection_i18n" (
    "id" TEXT NOT NULL,
    "collection_id" TEXT NOT NULL,
    "locale" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "subtitle" TEXT,
    "description" TEXT,
    "translation_status" "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "help_collection_i18n_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "help_collection_i18n_collection_id_locale_key" ON "help_collection_i18n"("collection_id", "locale");

CREATE TABLE IF NOT EXISTS "help_categories" (
    "id" TEXT NOT NULL,
    "collection_id" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    "is_published" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "help_categories_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "help_categories_collection_id_slug_key" ON "help_categories"("collection_id", "slug");
CREATE INDEX IF NOT EXISTS "help_categories_collection_id_idx" ON "help_categories"("collection_id");

CREATE TABLE IF NOT EXISTS "help_category_i18n" (
    "id" TEXT NOT NULL,
    "category_id" TEXT NOT NULL,
    "locale" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "description" TEXT,
    "translation_status" "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "help_category_i18n_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "help_category_i18n_category_id_locale_key" ON "help_category_i18n"("category_id", "locale");

CREATE TABLE IF NOT EXISTS "help_articles" (
    "id" TEXT NOT NULL,
    "category_id" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "status" "ContentStatus" NOT NULL DEFAULT 'DRAFT',
    "published_at" TIMESTAMP(3),
    "author_name" TEXT,
    "cover_media_id" TEXT,
    "allow_anchors" BOOLEAN NOT NULL DEFAULT true,
    "target_tags" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "help_articles_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "help_articles_category_id_slug_key" ON "help_articles"("category_id", "slug");
CREATE INDEX IF NOT EXISTS "help_articles_category_id_idx" ON "help_articles"("category_id");

CREATE TABLE IF NOT EXISTS "help_article_i18n" (
    "id" TEXT NOT NULL,
    "article_id" TEXT NOT NULL,
    "locale" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "standfirst" TEXT,
    "content_markdown" TEXT,
    "meta_title" TEXT,
    "meta_description" TEXT,
    "translation_status" "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "help_article_i18n_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "help_article_i18n_article_id_locale_key" ON "help_article_i18n"("article_id", "locale");

CREATE TABLE IF NOT EXISTS "help_article_blocks" (
    "id" TEXT NOT NULL,
    "article_id" TEXT NOT NULL,
    "locale" TEXT NOT NULL,
    "type" "ArticleBlockType" NOT NULL,
    "data" JSONB NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "help_article_blocks_pkey" PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS "help_article_blocks_article_id_locale_idx" ON "help_article_blocks"("article_id", "locale");

-- Contraintes FK (idempotent)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'help_collection_i18n_collection_id_fkey'
  ) THEN
    ALTER TABLE "help_collection_i18n" ADD CONSTRAINT "help_collection_i18n_collection_id_fkey"
      FOREIGN KEY ("collection_id") REFERENCES "help_collections"("id") ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'help_categories_collection_id_fkey'
  ) THEN
    ALTER TABLE "help_categories" ADD CONSTRAINT "help_categories_collection_id_fkey"
      FOREIGN KEY ("collection_id") REFERENCES "help_collections"("id") ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'help_category_i18n_category_id_fkey'
  ) THEN
    ALTER TABLE "help_category_i18n" ADD CONSTRAINT "help_category_i18n_category_id_fkey"
      FOREIGN KEY ("category_id") REFERENCES "help_categories"("id") ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'help_articles_category_id_fkey'
  ) THEN
    ALTER TABLE "help_articles" ADD CONSTRAINT "help_articles_category_id_fkey"
      FOREIGN KEY ("category_id") REFERENCES "help_categories"("id") ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'help_articles_cover_media_id_fkey'
  ) THEN
    ALTER TABLE "help_articles" ADD CONSTRAINT "help_articles_cover_media_id_fkey"
      FOREIGN KEY ("cover_media_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'help_article_i18n_article_id_fkey'
  ) THEN
    ALTER TABLE "help_article_i18n" ADD CONSTRAINT "help_article_i18n_article_id_fkey"
      FOREIGN KEY ("article_id") REFERENCES "help_articles"("id") ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'help_article_blocks_article_id_fkey'
  ) THEN
    ALTER TABLE "help_article_blocks" ADD CONSTRAINT "help_article_blocks_article_id_fkey"
      FOREIGN KEY ("article_id") REFERENCES "help_articles"("id") ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
END $$;
