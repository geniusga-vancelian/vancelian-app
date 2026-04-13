-- DropIndex
DROP INDEX IF EXISTS "articles_is_featured_idx";

-- DropIndex
DROP INDEX IF EXISTS "articles_is_highlighted_idx";

-- AlterTable
ALTER TABLE "pages" ADD COLUMN     "theme_color" TEXT NOT NULL DEFAULT 'dark';
