-- Tag de catégorie de page (localisé), distinct des champs méga-menu colonnes.
ALTER TABLE "page_i18n" ADD COLUMN IF NOT EXISTS "page_category_tag" VARCHAR(80);
