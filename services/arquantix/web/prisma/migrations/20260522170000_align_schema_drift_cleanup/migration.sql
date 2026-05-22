-- Nettoyage drift : index legacy articles remplacés par index partiels collection+slug (20260501140000).
DROP INDEX IF EXISTS "uq_articles_help_category_help_slug";
DROP INDEX IF EXISTS "uq_articles_academy_category_academy_slug";
