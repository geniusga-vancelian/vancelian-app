DO $$
BEGIN
  IF to_regclass('public.help_articles') IS NOT NULL THEN
    ALTER TABLE "help_articles"
    ADD COLUMN IF NOT EXISTS "target_tags" JSONB NOT NULL DEFAULT '[]'::jsonb;
  END IF;
END $$;
