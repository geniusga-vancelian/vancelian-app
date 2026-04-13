-- CreateTable
CREATE TABLE "article_block_i18n" (
    "id" TEXT NOT NULL,
    "block_id" TEXT NOT NULL,
    "locale" TEXT NOT NULL,
    "data" JSONB NOT NULL,
    "translation_status" "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "article_block_i18n_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "article_block_i18n_block_id_locale_key" ON "article_block_i18n"("block_id", "locale");

-- CreateIndex
CREATE INDEX "article_block_i18n_block_id_idx" ON "article_block_i18n"("block_id");

-- CreateIndex
CREATE INDEX "article_block_i18n_locale_idx" ON "article_block_i18n"("locale");

-- AddForeignKey
ALTER TABLE "article_block_i18n" ADD CONSTRAINT "article_block_i18n_block_id_fkey" FOREIGN KEY ("block_id") REFERENCES "article_blocks"("id") ON DELETE CASCADE ON UPDATE CASCADE;









