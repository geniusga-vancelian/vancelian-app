DO $$
BEGIN
  IF to_regclass('public.help_article_i18n') IS NOT NULL THEN
    ALTER TABLE "help_article_i18n"
    ADD COLUMN IF NOT EXISTS "content_markdown" TEXT;
  END IF;
END $$;
