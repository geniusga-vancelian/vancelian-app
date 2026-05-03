-- Article CMS : nouveau bloc d'article `HOW_IT_WORKS_CAROUSEL` (carrousel
-- d'étapes — calque de la section CMS `how_it_works`, rendu côté web via
-- `SectionHowItWorksCms` et côté mobile via le DS `HowItWorksCarousel`).
--
-- Migration **idempotente** : suit le pattern de
-- `20260425130000_article_block_type_enum_idempotent` pour rester safe sur
-- toute base déjà partiellement migrée (recover, restaurations, etc.) et ne
-- pas casser un déploiement où la valeur d'enum existerait déjà.
DO $enum_how_it_works_carousel$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_enum e
    INNER JOIN pg_type t ON e.enumtypid = t.oid
    WHERE t.typname = 'ArticleBlockType'
      AND e.enumlabel = 'HOW_IT_WORKS_CAROUSEL'
  ) THEN
    ALTER TYPE "ArticleBlockType" ADD VALUE 'HOW_IT_WORKS_CAROUSEL';
  END IF;
END
$enum_how_it_works_carousel$;
