-- CreateEnum
CREATE TYPE "ArticleBlockType" AS ENUM ('HEADING', 'PARAGRAPH', 'QUOTE', 'BULLET_LIST', 'IMAGE', 'VIDEO');

-- CreateTable
CREATE TABLE "articles" (
    "id" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "status" "ContentStatus" NOT NULL DEFAULT 'DRAFT',
    "published_at" TIMESTAMP(3),
    "updated_at" TIMESTAMP(3) NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "cover_media_id" TEXT NOT NULL,
    "author_name" TEXT NOT NULL,
    "author_role" TEXT,
    "allow_comments" BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT "articles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "article_i18n" (
    "id" TEXT NOT NULL,
    "article_id" TEXT NOT NULL,
    "locale" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "standfirst" TEXT NOT NULL,
    "meta_title" TEXT,
    "meta_description" TEXT,
    "translation_status" "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL',
    "updated_at" TIMESTAMP(3) NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "article_i18n_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "article_blocks" (
    "id" TEXT NOT NULL,
    "article_id" TEXT NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    "type" "ArticleBlockType" NOT NULL,
    "data" JSONB NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "article_blocks_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "articles_slug_key" ON "articles"("slug");

-- CreateIndex
CREATE INDEX "articles_status_idx" ON "articles"("status");

-- CreateIndex
CREATE INDEX "articles_published_at_idx" ON "articles"("published_at");

-- CreateIndex
CREATE UNIQUE INDEX "article_i18n_article_id_locale_key" ON "article_i18n"("article_id", "locale");

-- CreateIndex
CREATE INDEX "article_i18n_article_id_idx" ON "article_i18n"("article_id");

-- CreateIndex
CREATE UNIQUE INDEX "article_blocks_article_id_order_key" ON "article_blocks"("article_id", "order");

-- CreateIndex
CREATE INDEX "article_blocks_article_id_idx" ON "article_blocks"("article_id");

-- AddForeignKey
ALTER TABLE "articles" ADD CONSTRAINT "articles_cover_media_id_fkey" FOREIGN KEY ("cover_media_id") REFERENCES "media"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "article_i18n" ADD CONSTRAINT "article_i18n_article_id_fkey" FOREIGN KEY ("article_id") REFERENCES "articles"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "article_blocks" ADD CONSTRAINT "article_blocks_article_id_fkey" FOREIGN KEY ("article_id") REFERENCES "articles"("id") ON DELETE CASCADE ON UPDATE CASCADE;









