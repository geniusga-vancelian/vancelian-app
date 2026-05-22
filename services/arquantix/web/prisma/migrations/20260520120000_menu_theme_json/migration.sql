-- Thème visuel du menu primaire (palettes topnav par surface)
ALTER TABLE "menus" ADD COLUMN IF NOT EXISTS "theme_json" JSONB;
