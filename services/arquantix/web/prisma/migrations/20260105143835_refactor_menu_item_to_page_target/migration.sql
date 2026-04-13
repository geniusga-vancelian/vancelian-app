-- Step 1: Add new columns (nullable first)
ALTER TABLE "menu_items" ADD COLUMN "is_root" BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE "menu_items" ADD COLUMN "page_id" TEXT;

-- Step 2: Data migration
-- Convert existing items:
-- - If is_home = true => is_root = true, page_id = null
-- - Else: try to match by slug to find corresponding Page
DO $$
DECLARE
  item RECORD;
  matched_page_id TEXT;
BEGIN
  FOR item IN SELECT id, slug, is_home FROM menu_items LOOP
    IF item.is_home = true THEN
      -- Home item => is_root = true
      UPDATE menu_items SET is_root = true, page_id = NULL WHERE id = item.id;
    ELSIF item.slug IS NOT NULL AND item.slug != '' THEN
      -- Try to find matching Page by slug
      SELECT id INTO matched_page_id FROM pages WHERE slug = item.slug LIMIT 1;
      
      IF matched_page_id IS NOT NULL THEN
        -- Found matching page
        UPDATE menu_items SET is_root = false, page_id = matched_page_id WHERE id = item.id;
      ELSE
        -- No matching page found => disable item
        UPDATE menu_items SET enabled = false, is_root = false, page_id = NULL WHERE id = item.id;
        RAISE NOTICE 'MenuItem % (slug: %) has no matching Page - disabled', item.id, item.slug;
      END IF;
    ELSE
      -- No slug and not home => disable
      UPDATE menu_items SET enabled = false, is_root = false, page_id = NULL WHERE id = item.id;
      RAISE NOTICE 'MenuItem % has no slug and is not home - disabled', item.id;
    END IF;
  END LOOP;
END $$;

-- Step 3: Add foreign key constraint
ALTER TABLE "menu_items" ADD CONSTRAINT "menu_items_page_id_fkey" FOREIGN KEY ("page_id") REFERENCES "pages"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- Step 4: Create index on page_id
CREATE INDEX "menu_items_page_id_idx" ON "menu_items"("page_id");

-- Step 5: Drop old columns
ALTER TABLE "menu_items" DROP COLUMN "slug";
ALTER TABLE "menu_items" DROP COLUMN "is_home";
ALTER TABLE "menu_items" DROP COLUMN "url_path";









