-- Redondant avec nav_mega_category (libellé colonne méga-menu).
ALTER TABLE "page_i18n" DROP COLUMN IF EXISTS "page_category_tag";
