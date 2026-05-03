-- Champs optionnels méga-menu (pages enfants + i18n)
ALTER TABLE "pages" ADD COLUMN IF NOT EXISTS "nav_mega_icon_media_id" TEXT;

ALTER TABLE "page_i18n" ADD COLUMN IF NOT EXISTS "nav_mega_category" VARCHAR(120);
ALTER TABLE "page_i18n" ADD COLUMN IF NOT EXISTS "nav_mega_description" VARCHAR(500);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'pages_nav_mega_icon_media_id_fkey'
  ) THEN
    ALTER TABLE "pages"
      ADD CONSTRAINT "pages_nav_mega_icon_media_id_fkey"
      FOREIGN KEY ("nav_mega_icon_media_id") REFERENCES "media"("id")
      ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;
END $$;
