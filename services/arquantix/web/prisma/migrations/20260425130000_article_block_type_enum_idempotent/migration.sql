-- Blocs article CMS : s'assurer que l'enum PostgreSQL contient les variantes
-- KEY_INFORMATION, VIDEO_BLOCK_ARTICLE, STEPS_MODULE.
-- Idempotent (vérification pg_enum) : corrige les bases où les migrations
-- 20260424 / 20260425 n'ont pas été appliquées, sans échouer si elles l'ont déjà été.

DO $enum_key_information$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_enum e
    INNER JOIN pg_type t ON e.enumtypid = t.oid
    WHERE t.typname = 'ArticleBlockType'
      AND e.enumlabel = 'KEY_INFORMATION'
  ) THEN
    ALTER TYPE "ArticleBlockType" ADD VALUE 'KEY_INFORMATION';
  END IF;
END
$enum_key_information$;

DO $enum_video_block$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_enum e
    INNER JOIN pg_type t ON e.enumtypid = t.oid
    WHERE t.typname = 'ArticleBlockType'
      AND e.enumlabel = 'VIDEO_BLOCK_ARTICLE'
  ) THEN
    ALTER TYPE "ArticleBlockType" ADD VALUE 'VIDEO_BLOCK_ARTICLE';
  END IF;
END
$enum_video_block$;

DO $enum_steps$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_enum e
    INNER JOIN pg_type t ON e.enumtypid = t.oid
    WHERE t.typname = 'ArticleBlockType'
      AND e.enumlabel = 'STEPS_MODULE'
  ) THEN
    ALTER TYPE "ArticleBlockType" ADD VALUE 'STEPS_MODULE';
  END IF;
END
$enum_steps$;
