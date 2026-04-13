DO $$
BEGIN
  IF to_regclass('public.help_collections') IS NOT NULL THEN
    ALTER TABLE "help_collections"
    ADD COLUMN IF NOT EXISTS "icon_key" TEXT NOT NULL DEFAULT 'article',
    ADD COLUMN IF NOT EXISTS "color_hex" TEXT NOT NULL DEFAULT '#0F172A';
  END IF;
END $$;
