-- CreateEnum
CREATE TYPE "ArticleLinkKind" AS ENUM ('ASSET', 'VAULT');

-- CreateTable
CREATE TABLE "article_links" (
    "id" TEXT NOT NULL,
    "article_id" TEXT NOT NULL,
    "kind" "ArticleLinkKind" NOT NULL,
    "target_id" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "article_links_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "article_links_article_id_kind_target_id_key" ON "article_links"("article_id", "kind", "target_id");

-- CreateIndex
CREATE INDEX "article_links_article_id_idx" ON "article_links"("article_id");

-- CreateIndex
CREATE INDEX "article_links_kind_target_id_idx" ON "article_links"("kind", "target_id");

-- AddForeignKey
ALTER TABLE "article_links" ADD CONSTRAINT "article_links_article_id_fkey" FOREIGN KEY ("article_id") REFERENCES "articles"("id") ON DELETE CASCADE ON UPDATE CASCADE;
